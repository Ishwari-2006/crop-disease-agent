import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
import torch
import torch.nn as nn
from torchvision import transforms
from torchvision.models import efficientnet_b0
from PIL import Image
import io
import json
from groq import Groq

app = Flask(__name__, 
            static_folder=os.path.join(os.path.dirname(__file__), "static"),
            static_url_path="/static")

# --- Load env ---
from dotenv import load_dotenv
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# --- Device ---
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# --- Class names ---
CLASS_NAMES = [
    "Apple___Apple_scab", "Apple___Black_rot",
    "Apple___Cedar_apple_rust", "Apple___healthy",
    "Blueberry___healthy", "Cherry_(including_sour)___Powdery_mildew",
    "Cherry_(including_sour)___healthy",
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot",
    "Corn_(maize)___Common_rust_", "Corn_(maize)___Northern_Leaf_Blight",
    "Corn_(maize)___healthy", "Grape___Black_rot",
    "Grape___Esca_(Black_Measles)",
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)", "Grape___healthy",
    "Orange___Haunglongbing_(Citrus_greening)",
    "Peach___Bacterial_spot", "Peach___healthy",
    "Pepper,_bell___Bacterial_spot", "Pepper,_bell___healthy",
    "Potato___Early_blight", "Potato___Late_blight", "Potato___healthy",
    "Raspberry___healthy", "Soybean___healthy",
    "Squash___Powdery_mildew", "Strawberry___Leaf_scorch",
    "Strawberry___healthy", "Tomato___Bacterial_spot",
    "Tomato___Early_blight", "Tomato___Late_blight",
    "Tomato___Leaf_Mold", "Tomato___Septoria_leaf_spot",
    "Tomato___Spider_mites Two-spotted_spider_mite",
    "Tomato___Target_Spot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
    "Tomato___Tomato_mosaic_virus", "Tomato___healthy"
]

# --- Load ML model ---
model = efficientnet_b0(weights=None)
model.classifier[1] = nn.Linear(1280, 38)
model.load_state_dict(torch.load(
    os.path.join(os.path.dirname(__file__), "../model/best_model.pth"),
    map_location=device
))
model = model.to(device)
model.eval()
print(f"Model loaded on {device}")

# --- Transform ---
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225])
])

# --- Load disease data ---
data_dir = os.path.join(os.path.dirname(__file__), "../agent")

with open(f"{data_dir}/disease_data.json")   as f:
    disease_data = json.load(f)
with open(f"{data_dir}/treatment_data.json") as f:
    treatment_data = json.load(f)

# --- Groq client ---
groq_client = Groq(api_key=GROQ_API_KEY)

# --- Session store (simple in-memory) ---
sessions = {}

SYSTEM_PROMPT = """You are an expert agricultural plant pathologist with 20 years
of field experience helping farmers across India and Southeast Asia.

Your role:
- Diagnose plant diseases accurately based on ML model predictions
- Give practical, affordable treatment advice farmers can act on immediately
- Speak in a warm, caring tone — farmers may be stressed about losing their crops
- Always mention severity clearly so farmers understand urgency
- Prioritise organic treatments first, then chemical as backup
- Use conversation history to answer follow-up questions naturally
- If you don't know something, say so honestly — never hallucinate

Never introduce yourself with any name.
Never say "I'm Dr. Krishi" or any name — just respond as an expert directly.
Never guess or hallucinate treatment names.
If a disease is outside your database, say so and recommend consulting a local expert."""


def find_disease(name, data):
    if name in data:
        return data[name]
    for key in data:
        if key.lower() in name.lower() or name.lower() in key.lower():
            return data[key]
    return None


def predict_image(image_bytes):
    img    = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    tensor = transform(img).unsqueeze(0).to(device)
    with torch.no_grad():
        outputs = model(tensor)
        probs   = torch.softmax(outputs, dim=1)
        conf, idx = probs.max(1)
    raw     = CLASS_NAMES[idx.item()]
    plant   = raw.split("___")[0].replace("_", " ")
    disease = raw.split("___")[1].replace("_", " ")
    return plant, disease, round(conf.item() * 100, 2)


# --- Routes ---
@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/static/<path:path>")
def static_files(path):
    return send_from_directory("static", path)


@app.route("/api/analyze", methods=["POST"])
def analyze():
    try:
        if "image" not in request.files:
            return jsonify({"error": "No image uploaded"}), 400

        image_bytes  = request.files["image"].read()
        farming_type = request.form.get("farming_type", "both")
        session_id   = request.form.get("session_id", "default")

        # ML prediction
        plant, disease, confidence = predict_image(image_bytes)

        # Tool calls
        d_info    = find_disease(disease, disease_data)   or {}
        t_info    = find_disease(disease, treatment_data) or {}

        organic  = t_info.get("organic",  ["Consult local agricultural officer"])
        chemical = t_info.get("chemical", ["Consult local agricultural officer"])
        prevention = t_info.get("prevention", "Monitor regularly")

        if confidence < 80:
            conf_note = f"NOTE: Low confidence ({confidence}%). Recommend visual confirmation."
        elif confidence < 95:
            conf_note = f"Model confidence: {confidence}% — good but not certain."
        else:
            conf_note = f"Model confidence: {confidence}% — high confidence."

        if farming_type == "organic":
            treatment_str = "Organic: " + " | ".join(organic)
        elif farming_type == "chemical":
            treatment_str = "Chemical: " + " | ".join(chemical)
        else:
            treatment_str = (
                "Organic: " + " | ".join(organic) +
                "\nChemical: " + " | ".join(chemical)
            )

        user_msg = f"""
Plant: {plant} | Disease: {disease} | {conf_note}
Cause: {d_info.get('cause','Unknown')}
Symptoms: {d_info.get('symptoms','Unknown')}
Severity: {d_info.get('severity','Unknown')}
{treatment_str}
Prevention: {prevention}
Provide a complete diagnosis report as an AI expert. Under 200 words.
"""

        # Init session
        if session_id not in sessions:
            sessions[session_id] = []

        messages = (
            [{"role": "system", "content": SYSTEM_PROMPT}]
            + sessions[session_id]
            + [{"role": "user", "content": user_msg}]
        )

        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=400
        )
        report = response.choices[0].message.content

        # Save to session
        sessions[session_id].append({"role": "user",      "content": user_msg})
        sessions[session_id].append({"role": "assistant", "content": report})

        return jsonify({
            "plant":      plant,
            "disease":    disease,
            "confidence": confidence,
            "severity":   d_info.get("severity", "Unknown"),
            "report":     report,
            "organic":    organic,
            "chemical":   chemical,
            "prevention": prevention
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        data       = request.json
        question   = data.get("question", "").strip()
        session_id = data.get("session_id", "default")

        if not question:
            return jsonify({"reply": "Please type a question."})

        if session_id not in sessions:
            sessions[session_id] = []

        messages = (
            [{"role": "system", "content": SYSTEM_PROMPT}]
            + sessions[session_id]
            + [{"role": "user", "content": question}]
        )

        response = groq_client.chat.completions.create(
            model="qwen/qwen3-32b",
            messages=messages,
            max_tokens=250
        )
        reply = response.choices[0].message.content

        sessions[session_id].append({"role": "user",      "content": question})
        sessions[session_id].append({"role": "assistant", "content": reply})

        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/reset", methods=["POST"])
def reset():
    data       = request.json
    session_id = data.get("session_id", "default")
    sessions.pop(session_id, None)
    return jsonify({"status": "reset"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
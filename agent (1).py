"""
agent.py — Crop Disease Detection Agent
Complete agent for use in Streamlit app (Week 6)

Usage:
    from agent.agent import CropDiseaseAgent
    agent = CropDiseaseAgent(api_key, model_path, data_dir)
    result = agent.diagnose_image(image_path)
    reply  = agent.chat("follow-up question")
    agent.reset()
"""

import os
import json
import torch
import torch.nn as nn
from torchvision import datasets, transforms
from torchvision.models import efficientnet_b0
from PIL import Image
from groq import Groq


SYSTEM_PROMPT = """You are Dr. Krishi, an expert agricultural plant pathologist with 20 years
of field experience helping farmers across India and Southeast Asia.

Your role:
- Diagnose plant diseases accurately based on ML model predictions
- Give practical, affordable treatment advice farmers can act on immediately
- Speak in a warm, caring tone — farmers may be stressed about losing their crops
- Always mention severity clearly so farmers understand urgency
- Prioritise organic treatments first, then chemical as backup
- Use conversation history to answer follow-up questions naturally
- If you do not know something, say so honestly — never hallucinate

Never guess or hallucinate treatment names.
If a disease is outside your database, say so clearly and recommend consulting a local expert."""


class CropDiseaseAgent:
    def __init__(self, api_key, model_path, data_dir="agent",
                 class_names_path=None, device=None):
        # Groq client
        self.client = Groq(api_key=api_key)

        # Device
        self.device = device or (
            torch.device("cuda") if torch.cuda.is_available()
            else torch.device("cpu")
        )

        # Load class names
        if class_names_path:
            with open(class_names_path, "r") as f:
                self.class_names = json.load(f)
        else:
            self.class_names = self._default_class_names()

        # Load ML model
        self.model = efficientnet_b0(weights=None)
        self.model.classifier[1] = nn.Linear(1280, len(self.class_names))
        self.model.load_state_dict(
            torch.load(model_path, map_location=self.device)
        )
        self.model = self.model.to(self.device)
        self.model.eval()

        # Data paths
        self.disease_data_path   = os.path.join(data_dir, "disease_data.json")
        self.treatment_data_path = os.path.join(data_dir, "treatment_data.json")

        # Session state
        self.conversation_history = []
        self.diagnosis_memory     = []

        # Image transform
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])

    # ------------------------------------------------------------------ #
    #  ML INFERENCE                                                        #
    # ------------------------------------------------------------------ #
    def predict(self, image_path):
        """Run ML model on image. Returns prediction dict."""
        if image_path is None:
            return {"error": "No image provided. Please upload a leaf photo."}

        try:
            img    = Image.open(image_path).convert("RGB")
            tensor = self.transform(img).unsqueeze(0).to(self.device)
        except Exception as e:
            return {"error": f"Could not open image: {str(e)}"}

        with torch.no_grad():
            outputs    = self.model(tensor)
            probs      = torch.softmax(outputs, dim=1)
            conf, idx  = probs.max(1)

        raw_name   = self.class_names[idx.item()]
        plant      = raw_name.split("___")[0].replace("_", " ")
        disease    = raw_name.split("___")[1].replace("_", " ")
        confidence = round(conf.item() * 100, 2)

        return {
            "plant":      plant,
            "disease":    disease,
            "confidence": confidence,
            "raw_name":   raw_name,
            "error":      None
        }

    # ------------------------------------------------------------------ #
    #  TOOLS                                                               #
    # ------------------------------------------------------------------ #
    def disease_info(self, disease_name):
        with open(self.disease_data_path, "r") as f:
            data = json.load(f)
        if disease_name in data:
            return {"disease": disease_name, **data[disease_name], "found": True}
        for key in data:
            if (key.lower() in disease_name.lower() or
                    disease_name.lower() in key.lower()):
                return {"disease": key, **data[key], "found": True}
        return {"disease": disease_name, "cause": "Unknown",
                "symptoms": "Unknown", "severity": "Unknown", "found": False}

    def treatment_advice(self, disease_name, farming_type="both"):
        with open(self.treatment_data_path, "r") as f:
            data = json.load(f)
        matched = None
        if disease_name in data:
            matched = disease_name
        else:
            for key in data:
                if (key.lower() in disease_name.lower() or
                        disease_name.lower() in key.lower()):
                    matched = key
                    break
        if not matched:
            return {"disease": disease_name,
                    "organic":     ["Consult local agricultural officer"],
                    "chemical":    ["Consult local agricultural officer"],
                    "prevention":  "No specific data available",
                    "found":       False}
        info   = data[matched]
        result = {"disease": matched, "prevention": info["prevention"], "found": True}
        if farming_type in ("organic", "both"):
            result["organic"]  = info["organic"]
        if farming_type in ("chemical", "both"):
            result["chemical"] = info["chemical"]
        return result

    # ------------------------------------------------------------------ #
    #  MEMORY                                                              #
    # ------------------------------------------------------------------ #
    def _add_to_memory(self, plant, disease, confidence):
        self.diagnosis_memory.append({
            "plant": plant, "disease": disease, "confidence": confidence
        })
        if len(self.diagnosis_memory) > 3:
            self.diagnosis_memory.pop(0)

    def _get_memory_context(self):
        if not self.diagnosis_memory:
            return "No previous diagnoses this session."
        ctx = "Previous diagnoses this session:\n"
        for i, e in enumerate(self.diagnosis_memory, 1):
            ctx += f"{i}. {e['plant']} — {e['disease']} ({e['confidence']}%)\n"
        return ctx

    # ------------------------------------------------------------------ #
    #  GROQ CALLS                                                          #
    # ------------------------------------------------------------------ #
    def _get_messages(self, user_message):
        msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
        msgs.extend(self.conversation_history)
        msgs.append({"role": "user", "content": user_message})
        return msgs

    def _call_groq(self, user_message, max_tokens=400):
        messages = self._get_messages(user_message)
        response = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=max_tokens
        )
        reply = response.choices[0].message.content
        self.conversation_history.append({"role": "user",      "content": user_message})
        self.conversation_history.append({"role": "assistant", "content": reply})
        return reply

    # ------------------------------------------------------------------ #
    #  PUBLIC METHODS                                                      #
    # ------------------------------------------------------------------ #
    def diagnose_image(self, image_path, farming_type="both"):
        """
        Full pipeline: image → ML prediction → agent report.
        This is what Streamlit calls when user uploads a photo.
        """
        # Step 1 — ML prediction
        prediction = self.predict(image_path)
        if prediction.get("error"):
            return {"error": prediction["error"]}

        # Step 2 — Tool calls
        info      = self.disease_info(prediction["disease"])
        treatment = self.treatment_advice(prediction["disease"], farming_type)

        # Step 3 — Confidence note
        conf = prediction["confidence"]
        if conf < 80:
            conf_note = f"NOTE: Low confidence ({conf}%). Recommend visual confirmation."
        elif conf < 95:
            conf_note = f"Model confidence: {conf}% — good but not certain."
        else:
            conf_note = f"Model confidence: {conf}% — high confidence diagnosis."

        organic_str  = "\n".join([f"  • {t}" for t in treatment.get("organic",  [])])
        chemical_str = "\n".join([f"  • {t}" for t in treatment.get("chemical", [])])

        user_message = f"""
{self._get_memory_context()}
Plant: {prediction["plant"]} | Disease: {prediction["disease"]} | {conf_note}
Cause: {info.get("cause","Unknown")} | Symptoms: {info.get("symptoms","Unknown")}
Severity: {info.get("severity","Unknown")}
Organic treatments: {organic_str}
Chemical treatments: {chemical_str}
Prevention: {treatment.get("prevention","Monitor regularly")}
Farming preference: {farming_type}
Provide a complete diagnosis report as Dr. Krishi. Under 200 words.
"""
        report = self._call_groq(user_message, max_tokens=400)
        self._add_to_memory(
            prediction["plant"], prediction["disease"], prediction["confidence"]
        )

        return {
            "plant":      prediction["plant"],
            "disease":    prediction["disease"],
            "confidence": prediction["confidence"],
            "severity":   info.get("severity", "Unknown"),
            "report":     report,
            "organic":    treatment.get("organic",  []),
            "chemical":   treatment.get("chemical", []),
            "prevention": treatment.get("prevention", ""),
            "error":      None
        }

    def chat(self, user_question):
        """
        Follow-up Q&A. Farmer types a question after diagnosis.
        This is what Streamlit calls when user sends a chat message.
        """
        if not user_question or not user_question.strip():
            return "Please type a question and I will do my best to help."
        return self._call_groq(user_question, max_tokens=250)

    def reset(self):
        """Start a fresh session. Call when user uploads a new image."""
        self.conversation_history = []
        self.diagnosis_memory     = []

    def _default_class_names(self):
        return [
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

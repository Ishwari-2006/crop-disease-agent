import os
import json
from groq import Groq

SYSTEM_PROMPT = """You are Dr. Krishi, an expert agricultural plant pathologist with 20 years 
of field experience helping farmers across India and Southeast Asia.

Your role:
- Diagnose plant diseases accurately based on ML model predictions
- Give practical, affordable treatment advice farmers can act on immediately
- Speak in a warm, caring tone — farmers may be stressed about losing their crops
- Always mention severity clearly so farmers understand urgency
- Prioritise organic treatments first, then chemical as backup
- End every diagnosis with one key prevention tip for next season

Your response style:
- Clear headers for each section
- Simple language — avoid overly technical jargon
- Specific product names with generic alternatives in brackets
- Realistic about limitations — if confidence is below 80%, suggest getting a second opinion

You have access to a structured disease database and always base your advice on that data.
Never guess or hallucinate treatment names."""


def get_client(api_key):
    return Groq(api_key=api_key)


def disease_info(disease_name, data_path="agent/disease_data.json"):
    with open(data_path, "r") as f:
        data = json.load(f)
    if disease_name in data:
        info = data[disease_name]
        return {"disease": disease_name, **info, "found": True}
    for key in data:
        if key.lower() in disease_name.lower() or disease_name.lower() in key.lower():
            info = data[key]
            return {"disease": key, **info, "found": True}
    return {"disease": disease_name, "cause": "Unknown",
            "symptoms": "Unknown", "severity": "Unknown", "found": False}


def treatment_advice(disease_name, farming_type="both",
                     data_path="agent/treatment_data.json"):
    with open(data_path, "r") as f:
        data = json.load(f)
    matched_key = None
    if disease_name in data:
        matched_key = disease_name
    else:
        for key in data:
            if key.lower() in disease_name.lower() or disease_name.lower() in key.lower():
                matched_key = key
                break
    if not matched_key:
        return {"disease": disease_name,
                "organic": ["Consult local agricultural officer"],
                "chemical": ["Consult local agricultural officer"],
                "prevention": "No data available", "found": False}
    info   = data[matched_key]
    result = {"disease": matched_key, "prevention": info["prevention"], "found": True}
    if farming_type in ("organic", "both"):
        result["organic"]  = info["organic"]
    if farming_type in ("chemical", "both"):
        result["chemical"] = info["chemical"]
    return result


def run_expert_agent(plant, disease, confidence, client, farming_type="both"):
    info      = disease_info(disease)
    treatment = treatment_advice(disease, farming_type)

    if confidence < 80:
        confidence_note = f"NOTE: Model confidence is only {confidence}%. Recommend visual confirmation."
    elif confidence < 95:
        confidence_note = f"Model confidence: {confidence}% — good but not certain."
    else:
        confidence_note = f"Model confidence: {confidence}% — high confidence diagnosis."

    organic_str  = "\n".join([f"  • {t}" for t in treatment.get("organic", [])])
    chemical_str = "\n".join([f"  • {t}" for t in treatment.get("chemical", [])])

    user_message = f"""
Plant: {plant}
Diagnosed disease: {disease}
{confidence_note}

Disease database results:
- Cause: {info.get("cause", "Unknown")}
- Symptoms: {info.get("symptoms", "Unknown")}
- Severity: {info.get("severity", "Unknown")}

Treatment database results:
Organic options:
{organic_str}

Chemical options:
{chemical_str}

Prevention: {treatment.get("prevention", "Monitor regularly")}

Farming preference: {farming_type}

Please provide a complete diagnosis report as Dr. Krishi.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message}
        ],
        max_tokens=500
    )

    return response.choices[0].message.content

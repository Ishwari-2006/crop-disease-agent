# 🌿 Crop Disease Detection Agent

An end-to-end AI system that detects plant diseases from leaf photos and delivers expert treatment advice through an agentic AI pipeline.

![Python](https://img.shields.io/badge/Python-3.10-blue) ![PyTorch](https://img.shields.io/badge/PyTorch-2.x-orange) ![Flask](https://img.shields.io/badge/Flask-3.x-black) ![License](https://img.shields.io/badge/License-MIT-green)

---

## What it does

Upload a photo of a diseased leaf → the ML model identifies the disease → an AI agent returns a structured diagnosis with organic and chemical treatment options → you can ask follow-up questions in a chat interface.

**Live demo:** _coming soon_

---

## Pipeline overview

```
Leaf photo
    ↓
EfficientNet-B0 (fine-tuned)
    ↓
Disease name + confidence %
    ↓
Tool 1: disease_info()      → cause, symptoms, severity
Tool 2: treatment_advice()  → organic + chemical treatments
    ↓
Llama 3.3 (via Groq API)
    ↓
Expert diagnosis report + follow-up Q&A
```

---

## Key results

| Metric | Value |
|---|---|
| Model | EfficientNet-B0 (transfer learning) |
| Dataset | PlantVillage — 54,305 images, 38 classes |
| Validation accuracy | 99.56% |
| Training epochs | 5 (fine-tuned, all layers unfrozen) |
| Inference time | ~200ms on CPU |

> **Note:** The model is trained on controlled lab images. Real-world field photos with complex backgrounds may yield lower confidence. For best results, photograph a single leaf against a plain background.

---

## Features

- 38 disease classes across 12 plant species
- Transfer learning with EfficientNet-B0 pretrained on ImageNet
- Agentic AI with tool calling — agent decides what data to fetch before answering
- Session memory — agent remembers last 3 diagnoses per session
- Follow-up Q&A chat — ask anything after a diagnosis
- Organic vs chemical treatment filter
- Flask REST API backend
- Pure HTML/CSS/JS frontend — no framework dependencies

---

## Project structure

```
crop-disease-agent/
├── notebooks/
│   ├── day6_training_loop.ipynb
│   ├── day7_accuracy_curves.ipynb
│   ├── day10_data_augmentation.ipynb
│   ├── day11_finetune.ipynb
│   ├── day12_confusion_matrix.ipynb
│   └── day13_inference.ipynb
├── agent/
│   ├── agent.py
│   ├── disease_data.json
│   └── treatment_data.json
├── model/
│   └── best_model.pth
├── app/
│   ├── server.py
│   └── static/
│       ├── index.html
│       ├── style.css
│       └── app.js
├── .env
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Tech stack

| Layer | Technology |
|---|---|
| ML model | PyTorch, EfficientNet-B0, torchvision |
| Dataset | PlantVillage (Kaggle) |
| LLM | Llama 3.3 70B via Groq API |
| Backend | Flask |
| Frontend | HTML, CSS, JavaScript |
| Environment | Google Colab (T4 GPU for training), local CPU for inference |

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/Ishwari-2006/crop-disease-agent.git
cd crop-disease-agent
```

### 2. Create virtual environment

```bash
python -m venv venv
venv\Scripts\activate       # Windows
source venv/bin/activate    # Mac/Linux
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Add environment variables

Create a `.env` file in the project root:

```
GROQ_API_KEY=your_groq_api_key_here
```

Get a free Groq API key at [console.groq.com](https://console.groq.com)

### 5. Add the model weights

Download `best_model.pth` and place it in the `model/` folder. The file is not included in this repo due to size — retrain using `notebooks/day11_finetune.ipynb` on Google Colab, or contact me for the weights.

### 6. Run the app

```bash
python app/server.py
```

Open `http://127.0.0.1:5000` in your browser.

---

## Supported plants and diseases

| Plant | Diseases detected |
|---|---|
| Apple | Apple scab, Black rot, Cedar apple rust, Healthy |
| Grape | Black rot, Esca (Black Measles), Leaf blight, Healthy |
| Tomato | Bacterial spot, Early blight, Late blight, Leaf mold, Septoria leaf spot, Spider mites, Target spot, Yellow leaf curl virus, Mosaic virus, Healthy |
| Potato | Early blight, Late blight, Healthy |
| Corn | Cercospora leaf spot, Common rust, Northern leaf blight, Healthy |
| Peach | Bacterial spot, Healthy |
| Pepper | Bacterial spot, Healthy |
| Strawberry | Leaf scorch, Healthy |
| Orange | Haunglongbing (Citrus greening) |
| Cherry | Powdery mildew, Healthy |
| Blueberry | Healthy |
| Soybean | Healthy |

---

## Training details

Training was done in stages on Google Colab (T4 GPU):

**Stage 1 — Feature extraction** (day6): Froze all EfficientNet layers except the final classifier. Trained 3 epochs. Val accuracy: 96.62%.

**Stage 2 — Data augmentation** (day10): Added random flip, colour jitter, random crop. Retrained frozen model. Val accuracy: 93.31% (lower score, harder training — expected).

**Stage 3 — Full fine-tuning** (day11): Unfroze all layers, reduced learning rate to 0.0001, trained 5 epochs with augmentation. Val accuracy: 99.56%.

---

## API endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/analyze` | Upload leaf image, get diagnosis |
| POST | `/api/chat` | Send follow-up question |
| POST | `/api/reset` | Reset session memory |

### Example: `/api/analyze`

```bash
curl -X POST http://localhost:5000/api/analyze \
  -F "image=@leaf.jpg" \
  -F "farming_type=organic" \
  -F "session_id=abc123"
```

Response:
```json
{
  "plant": "Tomato",
  "disease": "Late blight",
  "confidence": 99.9,
  "severity": "High",
  "report": "...",
  "organic": ["Apply copper-based fungicide immediately", "..."],
  "chemical": ["Apply Chlorothalonil (Daconil)...", "..."],
  "prevention": "Use certified disease-free seeds..."
}
```

---

## Known limitations

- Trained on lab-controlled PlantVillage images — real field photos with soil, shadows, or multiple leaves reduce confidence
- Disease database covers 28 of 38 classes with detailed treatment data — remaining classes fall back to general advice
- Session memory is in-memory only — restarting the server clears all sessions
- Model runs on CPU locally — inference is ~200ms per image

---

## Requirements

```
torch
torchvision
flask
groq
python-dotenv
pillow
```

Full list in `requirements.txt`.

---

## License

MIT License — free to use, modify, and distribute.

---

## Author

**Ishwari Rautray**
[GitHub](https://github.com/Ishwari-2006)

---

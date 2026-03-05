from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import torch.nn.functional as F

app = FastAPI(title="GoEmotions Multi-Label Service")

MODEL_NAME ="monologg/bert-base-cased-goemotions-original"  # multi-label

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)

model.eval()

class JournalInput(BaseModel):
    text: str

@app.post("/predict")
def predict_emotions(data: JournalInput):
    inputs = tokenizer(
        data.text,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=128,
    )

    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
        probs = torch.sigmoid(logits)[0]  # 🔥 sigmoid, not softmax

    labels = model.config.id2label

    emotions = {
        labels[i]: round(probs[i].item(), 4)
        for i in range(len(probs))
        if probs[i] > 0.2   # threshold (tunable)
    }

    return emotions

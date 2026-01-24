from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import torch.nn.functional as F

app = FastAPI(title="Emotion Detection Service")

MODEL_NAME = "bhadresh-savani/distilbert-base-uncased-emotion"

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)

model.eval()

class JournalInput(BaseModel):
    text: str

@app.post("/predict")
def predict_emotion(data: JournalInput):
    inputs = tokenizer(
        data.text,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=128,
    )

    with torch.no_grad():
        outputs = model(**inputs)
        probs = F.softmax(outputs.logits, dim=1)

    scores = probs[0].tolist()
    labels = model.config.id2label

    emotions = {
        labels[i]: round(scores[i], 4)
        for i in range(len(scores))
        if scores[i] > 0.05
    }

    return emotions

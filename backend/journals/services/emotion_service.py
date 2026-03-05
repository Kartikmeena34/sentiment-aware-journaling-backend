import requests
import os

HF_API_URL = "https://api-inference.huggingface.co/models/monologg/bert-base-cased-goemotions-original"

headers = {
    "Authorization": f"Bearer {os.environ.get('HF_TOKEN')}"
}


def predict_emotions(text):
    payload = {"inputs": text}

    response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=20)
    data = response.json()

    # Handle model loading response
    if isinstance(data, dict) and "error" in data:
        raise ValueError(data["error"])

    # HF sometimes returns nested list
    if isinstance(data, list) and isinstance(data[0], list):
        data = data[0]

    emotion_scores = {item["label"]: item["score"] for item in data}

    return emotion_scores


def detect_emotion(text):
    result = predict_emotions(text)

    if not result:
        raise ValueError("Empty prediction result")

    dominant = max(result, key=result.get)
    confidence = result[dominant]

    return {
        "dominant_emotion": dominant,
        "confidence": confidence,
        "raw": result
    }
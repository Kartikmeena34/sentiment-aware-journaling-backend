import requests

import requests

AI_URL = "http://localhost:8001/predict"

def detect_emotion(text):
    resp = requests.post(AI_URL, json={"text": text}, timeout=5)
    resp.raise_for_status()
    result = resp.json()

    if not result:
        raise ValueError("Empty prediction result")

    dominant = max(result, key=result.get)
    confidence = result[dominant]

    return {
        "dominant_emotion": dominant,
        "confidence": confidence,
        "raw": result
    }
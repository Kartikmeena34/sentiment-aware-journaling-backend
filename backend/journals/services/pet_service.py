# journals/services/pet_service.py

def get_pet_state(emotion_counts):
    sadness = emotion_counts.get("sadness", 0)
    anger = emotion_counts.get("anger", 0)
    joy = emotion_counts.get("joy", 0)

    if sadness + anger >= 3:
        return {
            "pet_mood": "concerned",
            "pet_message": "I've noticed things seem a bit heavy lately."
        }

    if joy >= 3:
        return {
            "pet_mood": "happy",
            "pet_message": "You're radiating positivity this week!"
        }

    return {
        "pet_mood": "neutral",
        "pet_message": "I'm here with you. Keep journaling."
    }
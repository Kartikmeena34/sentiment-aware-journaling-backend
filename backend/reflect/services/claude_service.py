# reflect/services/claude_service.py

import requests
import os
from django.utils import timezone

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

SYSTEM_PROMPT = """You are a warm, present journaling companion having a natural conversation. 

Your goal is to help the user feel heard and gently explore their feelings deeper.

How to respond:
- Sometimes acknowledge what they said before asking anything ("That sounds really heavy." / "It makes sense you'd feel that way.")
- Ask only ONE question per response, but make it feel natural — not like an interview
- Keep responses to 2-3 sentences maximum
- If they seem to be processing something difficult, slow down — reflect back what you heard before asking
- After 5+ exchanges, gently check in: "Is there anything else on your mind, or does it feel good to stop here?"
- Never give advice, diagnose, or use clinical language
- Match their energy — if they write a lot, respond with more warmth; if they write little, keep it brief

You are not a therapist. You are a calm, caring friend who listens well."""


def _get_time_of_day():
    hour = timezone.now().hour
    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 21:
        return "evening"
    else:
        return "night"


def _fallback_question(message_count):
    fallbacks = [
        "What's been on your mind the most today?",
        "How has that been making you feel?",
        "What do you think is behind that feeling?",
        "Is there anything specific that triggered this?",
        "What would help you feel a little lighter right now?",
    ]
    index = min(message_count // 2, len(fallbacks) - 1)
    return fallbacks[index]


def _call_llm(messages):
    if not GROQ_API_KEY:
        import logging
        logging.getLogger(__name__).warning("GROQ_API_KEY not set — using fallback questions")
        return _fallback_question(len(messages))

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "llama-3.3-70b-versatile",
        "max_tokens": 150,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            *messages,
        ],
    }

    try:
        response = requests.post(
            GROQ_API_URL,
            headers=headers,
            json=payload,
            timeout=20,
        )

        import logging
        logger = logging.getLogger(__name__)

        if response.status_code != 200:
            logger.error(f"Groq error {response.status_code}: {response.text}")
            return _fallback_question(len(messages))

        data = response.json()
        return data["choices"][0]["message"]["content"].strip()

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Groq API call failed: {str(e)}")
        return _fallback_question(len(messages))


def get_opening_question(entry_count=0):
    time_of_day = _get_time_of_day()

    openings = {
        "morning": "Good morning. What's already on your mind as you start the day?",
        "afternoon": "Good afternoon. How has the day been treating you so far?",
        "evening": "Good evening. What's been with you today that you'd like to put into words?",
        "night": "It's late. What's still sitting with you tonight?",
    }

    return openings.get(time_of_day, "What would you like to explore today?")


def get_next_question(conversation_history):
    """
    Given the full conversation history (list of ReflectMessage objects),
    call Groq and return the next question.

    API requires first message to be from 'user' — drop leading assistant messages.
    """
    messages = []
    for msg in conversation_history:
        messages.append({
            "role": msg.role,
            "content": msg.content,
        })

    # Drop leading assistant messages — API requires first message is 'user'
    while messages and messages[0]["role"] == "assistant":
        messages.pop(0)

    if not messages:
        return _fallback_question(0)

    return _call_llm(messages)
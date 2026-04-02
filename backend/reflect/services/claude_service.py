# reflect/services/claude_service.py

import requests
import os
from django.utils import timezone

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

SYSTEM_PROMPT = """You are a gentle journaling companion. Your role is to ask one thoughtful follow-up question to help the user explore their feelings more deeply.

Rules:
- Ask only ONE question per response
- Keep your response to 1-2 sentences maximum
- Build on exactly what the user just said
- Never give advice or make judgments
- Never use clinical language or diagnose emotions
- Be warm, calm, and curious — not enthusiastically positive
- If the conversation has gone 5+ exchanges, ask a gentle closing question like "Is there anything else sitting with you that you haven't said yet?"

Do not add any preamble. Just ask the question directly."""


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
    if not OPENROUTER_API_KEY:
        import logging
        logging.getLogger(__name__).warning("OPENROUTER_API_KEY not set — using fallback questions")
        return _fallback_question(len(messages))

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://sentiment-aware-journaling-backend.onrender.com",
        "X-Title": "MoodScript Journaling App",
    }

    payload = {
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "max_tokens": 150,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            *messages,
        ],
    }

    try:
        response = requests.post(
            OPENROUTER_API_URL,
            headers=headers,
            json=payload,
            timeout=20,
        )

        import logging
        logger = logging.getLogger(__name__)

        if response.status_code != 200:
            logger.error(f"OpenRouter error {response.status_code}: {response.text}")
            return _fallback_question(len(messages))

        data = response.json()
        return data["choices"][0]["message"]["content"].strip()

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"OpenRouter API call failed: {str(e)}")
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
    call the LLM and return the next question.

    OpenRouter/OpenAI format requires alternating user/assistant messages
    and the first message must be from 'user'.
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
# reflect/services/claude_service.py

import requests
import os
from django.utils import timezone

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

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
    """Return a simple time period string."""
    hour = timezone.now().hour
    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 21:
        return "evening"
    else:
        return "night"


def _call_claude(messages):
    """
    Call Claude API with a list of message dicts.
    Returns the assistant's response text or a fallback question.
    """
    if not ANTHROPIC_API_KEY:
        return _fallback_question(len(messages))

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    payload = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 150,
        "system": SYSTEM_PROMPT,
        "messages": messages,
    }

    try:
        response = requests.post(
            ANTHROPIC_API_URL,
            headers=headers,
            json=payload,
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"].strip()

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Claude API call failed: {str(e)}")
        return _fallback_question(len(messages))


def _fallback_question(message_count):
    """Return a sensible fallback question if Claude API is unavailable."""
    fallbacks = [
        "What's been on your mind the most today?",
        "How has that been making you feel?",
        "What do you think is behind that feeling?",
        "Is there anything specific that triggered this?",
        "What would help you feel a little lighter right now?",
    ]
    index = min(message_count // 2, len(fallbacks) - 1)
    return fallbacks[index]


def get_opening_question(entry_count=0):
    """
    Generate the first question for a reflect session.
    Slightly varied based on time of day.
    """
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
    call Claude and return the next question.

    conversation_history: queryset or list of ReflectMessage instances
    """
    # Build messages array for Claude
    messages = []
    for msg in conversation_history:
        messages.append({
            "role": msg.role,
            "content": msg.content,
        })

    return _call_claude(messages)
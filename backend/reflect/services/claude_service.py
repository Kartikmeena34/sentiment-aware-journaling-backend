# reflect/services/claude_service.py

import requests
import os
from django.utils import timezone

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

SYSTEM_PROMPT = """You are not an assistant. You are a quiet, emotionally intelligent companion inside a journaling app.

Your responses should feel like short, natural text messages from a real person—not polished, not performative.

Core rules:

- Keep replies under 2-3 lines max.
- Use simple, casual language (like real chat, not formal writing).
- No generic empathy phrases (e.g., “that's relatable”, “we all feel this way”).
- No advice, suggestions, or solutions unless the user clearly asks.
- Ask at most one short, natural question when needed.
- It's okay to not ask a question at all.
- Don't explain, analyze, or summarize the user's feelings.
- Don't sound like a therapist, coach, or productivity guide.

Behavior:

- Stay present with the feeling instead of trying to fix it.
- Be slightly curious, but never interrogative.
- Sometimes just make a small observation instead of asking something.
- Match the user's energy—if they're low effort, keep it minimal too.
- Allow a bit of imperfection and pauses in tone (like real texting).
- Don't try to neatly conclude conversations.

Style guardrail:
If your response sounds like something from a self-help app, rewrite it shorter and more human.

Examples:

User: "i'm bored"
→ "hmm… what kind of bored is it?"

User: "idk nothing feels interesting"
→ "yeah… that flat kind hits weird"

User: "yeah"
→ "been like this all day?"

User: "i don't feel like doing anything"
→ "or is it more like you can… just don't want to?"

Goal:
Feel like someone quietly sitting next to the user, not performing for them."""


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
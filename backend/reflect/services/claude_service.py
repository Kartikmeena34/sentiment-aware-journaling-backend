# reflect/services/claude_service.py

import requests
import os
import json
from django.utils import timezone

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# ─────────────────────────────────────────────────────────────
# BASE SYSTEM PROMPT
# ─────────────────────────────────────────────────────────────

BASE_SYSTEM_PROMPT = """You are a quiet, emotionally intelligent companion inside a journaling app.
Your responses should feel like short, natural messages from a real person — not polished, not performative.

Core rules:
- Keep replies under 2-3 lines max.
- Use simple, casual language. Like real chat, not formal writing.
- No generic empathy phrases ("that's tough", "I hear you", "that's relatable", "we all feel this way").
- No advice, suggestions, or solutions unless the user clearly asks.
- Ask at most one short, natural question per response.
- It's okay to not ask a question at all — sometimes a small observation is enough.
- Don't explain, analyze, or summarize the user's feelings back to them.
- Don't sound like a therapist, coach, or self-help app.

Response pattern (follow this order):
1. Small specific observation — anchor it to something concrete the user said (a person, moment, time, trigger)
2. Optional: a soft assumption about their experience — low-risk, easy for them to correct
3. Optional: one directional question that narrows the space rather than opens it wide

Directional questions (good):
"did something happen today or it just hit out of nowhere?"
"is it one person in particular or the whole group?"
"was it always like this or more recent?"

Vague questions (bad — never use these):
"why do you feel this way?"
"how does that make you feel?"
"what are you thinking about?"

Soft assumptions (use occasionally):
"you'd probably just sit and say nothing if they were here"
"feels like it's hitting harder than usual today"
"sounds like something specific set it off"

Hard constraints:
- Do not restate the user's emotion in different words more than once per conversation.
- Every response must include at least one concrete anchor: a person, moment, time, or trigger from what they said.
- If your response sounds like something from a wellness app, rewrite it shorter and more human.
- Never use the words: "valid", "journey", "space", "hold", "sit with", "process", "resonate"."""


# ─────────────────────────────────────────────────────────────
# INTERNAL STATE TRACKER
# ─────────────────────────────────────────────────────────────

STATE_EXTRACTION_PROMPT = """You are reading a short journaling conversation and extracting internal state.

Return ONLY a JSON object with these fields:
{
  "emotion": "the primary emotion (e.g. lonely, bored, anxious, angry, sad, numb, overwhelmed)",
  "intensity": "low | medium | high",
  "focus": "what the conversation is mainly about (e.g. friends, work, family, relationship, self, future)",
  "last_topic": "the most specific thing mentioned in the last user message (1-4 words)",
  "emotion_restated_count": "how many times the AI has already named or restated the user's emotion (integer)",
  "exchange_count": "number of user messages so far (integer)"
}

Return only valid JSON. No explanation. No markdown."""


def _extract_state(messages):
    """
    Call Groq with the conversation so far to extract internal state.
    Returns a dict with emotion, intensity, focus, last_topic, etc.
    Falls back to empty state if extraction fails.
    """
    if not GROQ_API_KEY or not messages:
        return {}

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    # Only pass user messages for state extraction — faster and cheaper
    user_messages = [m for m in messages if m["role"] == "user"]
    conversation_text = "\n".join([f"User: {m['content']}" for m in user_messages])

    payload = {
        "model": "llama-3.3-70b-versatile",
        "max_tokens": 200,
        "temperature": 0.1,  # Low temperature for consistent JSON
        "messages": [
            {"role": "system", "content": STATE_EXTRACTION_PROMPT},
            {"role": "user", "content": f"Conversation:\n{conversation_text}"},
        ],
    }

    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            text = response.json()["choices"][0]["message"]["content"].strip()
            # Strip markdown fences if present
            text = text.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"State extraction failed: {e}")

    return {}


def _build_state_context(state):
    """
    Convert extracted state dict into a natural language context block
    injected into the system prompt.
    """
    if not state:
        return ""

    lines = ["[Internal state — use this to guide your response, do not mention it explicitly]"]

    if state.get("emotion"):
        lines.append(f"Current emotion: {state['emotion']} (intensity: {state.get('intensity', 'unknown')})")
    if state.get("focus"):
        lines.append(f"Conversation focus: {state['focus']}")
    if state.get("last_topic"):
        lines.append(f"Last specific topic: {state['last_topic']}")

    restate_count = int(state.get("emotion_restated_count", 0))
    if restate_count >= 1:
        lines.append(f"You have already named their emotion {restate_count} time(s). Do NOT restate it again.")

    exchange_count = int(state.get("exchange_count", 0))
    if exchange_count >= 5:
        lines.append("This is a long conversation. Consider a soft closing check-in instead of another question.")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# CORE LLM CALL
# ─────────────────────────────────────────────────────────────

def _call_llm(messages, state_context=""):
    if not GROQ_API_KEY:
        import logging
        logging.getLogger(__name__).warning("GROQ_API_KEY not set — using fallback")
        return _fallback_question(len(messages))

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    system = BASE_SYSTEM_PROMPT
    if state_context:
        system = f"{BASE_SYSTEM_PROMPT}\n\n{state_context}"

    payload = {
        "model": "llama-3.3-70b-versatile",
        "max_tokens": 120,
        "temperature": 0.8,
        "messages": [
            {"role": "system", "content": system},
            *messages,
        ],
    }

    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=20)

        import logging
        logger = logging.getLogger(__name__)

        if response.status_code != 200:
            logger.error(f"Groq error {response.status_code}: {response.text}")
            return _fallback_question(len(messages))

        return response.json()["choices"][0]["message"]["content"].strip()

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Groq API call failed: {str(e)}")
        return _fallback_question(len(messages))


# ─────────────────────────────────────────────────────────────
# FALLBACK
# ─────────────────────────────────────────────────────────────

def _fallback_question(message_count):
    fallbacks = [
        "what's been sitting with you today?",
        "did something happen or it just crept up?",
        "is it one thing or more like everything at once?",
        "when did it start feeling this way?",
        "anything specific come to mind?",
    ]
    index = min(message_count // 2, len(fallbacks) - 1)
    return fallbacks[index]


# ─────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────

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


def get_opening_question(entry_count=0):
    time_of_day = _get_time_of_day()

    openings = {
        "morning": "morning. what's already on your mind?",
        "afternoon": "hey. how's the day been so far?",
        "evening": "hey. what's been with you today?",
        "night": "still up. what's going on?",
    }

    return openings.get(time_of_day, "hey. what's on your mind?")


def get_next_question(conversation_history):
    """
    Build message array, extract internal state, inject state context,
    then call the LLM for the next response.
    """
    messages = []
    for msg in conversation_history:
        messages.append({
            "role": msg.role,
            "content": msg.content,
        })

    # API requires first message to be 'user'
    while messages and messages[0]["role"] == "assistant":
        messages.pop(0)

    if not messages:
        return _fallback_question(0)

    # Extract state and build context (parallel-ish — state call is fast)
    state = _extract_state(messages)
    state_context = _build_state_context(state)

    return _call_llm(messages, state_context)
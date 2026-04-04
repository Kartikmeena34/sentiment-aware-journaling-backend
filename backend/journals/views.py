from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError

from .models import Journal
from .services.emotion_service import detect_emotion
from .services.analytics_service import compute_user_analytics
from .services.insight_service import generate_insight, generate_multiple_insights

import logging
import requests
import os
import json

logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_journal(request):
    logger.info(f"Journal request received from user {request.user.username}")

    text = request.data.get("text")

    if not text or not text.strip():
        raise ValidationError("Text is required")

    if len(text) > 2000:
        raise ValidationError("Text exceeds 2000 characters")

    journal = Journal.objects.create(user=request.user, text=text)
    logger.info(f"Journal {journal.id} saved (initial save)")

    try:
        emotion_data = detect_emotion(text)
        journal.emotion_data = emotion_data["raw"]
        journal.dominant_emotion = emotion_data["dominant_emotion"]
        journal.confidence = emotion_data["confidence"]
        journal.save()
        logger.info(f"Emotion detected for journal {journal.id}: {journal.dominant_emotion}")
    except Exception as e:
        logger.error(f"Emotion detection failed for journal {journal.id}: {str(e)}")

    analytics = compute_user_analytics(request.user)

    contextual_message = None
    if analytics.get("data_sufficiency"):
        baseline_shifts = analytics.get("baseline_shifts", {})
        if baseline_shifts:
            contextual_message = "This entry feels different from your recent ones."
        elif analytics.get("emotional_entropy", 0) >= 2.0:
            contextual_message = "You expressed a lot of different feelings today."

    return Response({
        "journal_id": journal.id,
        "dominant_emotion": journal.dominant_emotion,
        "confidence": journal.confidence,
        "contextual_message": contextual_message,
        "has_insights": analytics.get("data_sufficiency", False),
        "crisis_flag": analytics.get("crisis_flag", False),
    })


class UserAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        logger.info(f"Analytics requested by user {request.user.username}")
        analytics = compute_user_analytics(request.user)
        return Response(analytics)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_insights(request):
    logger.info(f"Insights requested by user {request.user.username}")
    analytics = compute_user_analytics(request.user)
    format_type = request.query_params.get("format", "multiple")

    if format_type == "single":
        insight = generate_insight(analytics)
        return Response({
            "insight": insight,
            "data_sufficiency": analytics.get("data_sufficiency", False),
            "weekly_confidence": analytics.get("weekly_confidence", 0.0)
        })
    else:
        insights = generate_multiple_insights(analytics)
        return Response({
            "insights": insights,
            "data_sufficiency": analytics.get("data_sufficiency", False),
            "weekly_confidence": analytics.get("weekly_confidence", 0.0),
            "crisis_flag": analytics.get("crisis_flag", False),
        })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def journal_history(request):
    journals = (
        Journal.objects
        .filter(user=request.user)
        .order_by("-created_at")
    )

    data = [
        {
            "id": j.id,
            "text": j.text,
            "dominant_emotion": j.dominant_emotion,
            "confidence": j.confidence,
            "created_at": j.created_at,
        }
        for j in journals
    ]

    return Response(data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def save_reflection(request):
    journal_id = request.data.get("journal_id")
    conversation = request.data.get("conversation", [])

    if not journal_id:
        return Response({"saved": False, "reason": "no journal_id"})

    try:
        journal = Journal.objects.get(id=journal_id, user=request.user)
        # Save full conversation as JSON string in reflection_answer
        if conversation:
            journal.reflection_question = conversation[0].get("content", "") if conversation else ""
            journal.reflection_answer = json.dumps(conversation)
        journal.save()
        return Response({"saved": True})
    except Journal.DoesNotExist:
        return Response({"saved": False, "reason": "not found"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reflect_chat(request):
    """
    Multi-turn reflection chat endpoint.
    Receives full conversation history each turn, returns next AI message.
    """
    journal_text = request.data.get("journal_text", "")
    dominant_emotion = request.data.get("dominant_emotion", "neutral")
    # conversation_history: list of {role: "user"/"assistant", content: "..."}
    conversation_history = request.data.get("conversation_history", [])

    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

    FALLBACK_QUESTIONS = [
        "What felt most significant about what you wrote?",
        "What do you think is underneath that feeling?",
        "Has this come up for you before?",
        "What would you want to remember about this moment?",
        "Is there something you haven't let yourself fully think about yet?",
    ]

    if not GROQ_API_KEY:
        # Rotate through fallback questions based on conversation length
        idx = len(conversation_history) // 2 % len(FALLBACK_QUESTIONS)
        return Response({"reply": FALLBACK_QUESTIONS[idx]})

    system_prompt = f"""You are a warm, empathetic journaling companion having a genuine conversation with someone who just wrote a journal entry.

The user's journal entry:
\"\"\"{journal_text}\"\"\"
Detected emotional tone: {dominant_emotion}

Your role:
- Have a real, flowing conversation — not a questionnaire
- Ask one thoughtful follow-up at a time, naturally woven into your response
- Acknowledge what the user says before asking the next thing
- Go deeper gradually — don't rush to conclusions
- Sound like a caring, curious friend — not a therapist or a bot
- Keep responses concise: 1-3 sentences maximum
- After 6+ exchanges, you can offer a warm, grounding closing thought instead of another question — but only if it feels natural
- Never say "I'm an AI" or refer to yourself as an assistant
- Never use bullet points or lists"""

    messages = [{"role": "system", "content": system_prompt}]

    # If no history yet, generate the opening question
    if not conversation_history:
        messages.append({
            "role": "user",
            "content": f"I just wrote this journal entry: \"{journal_text}\""
        })
    else:
        # Build conversation from history
        # First message is always the journal entry context
        messages.append({
            "role": "user",
            "content": f"I just wrote this journal entry: \"{journal_text}\""
        })
        messages.extend(conversation_history)

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "max_tokens": 200,
                "temperature": 0.85,
                "messages": messages,
            },
            timeout=15,
        )
        data = response.json()
        reply = data["choices"][0]["message"]["content"].strip()
        return Response({"reply": reply})

    except Exception as e:
        logger.error(f"Groq chat failed: {str(e)}")
        idx = len(conversation_history) // 2 % len(FALLBACK_QUESTIONS)
        return Response({"reply": FALLBACK_QUESTIONS[idx]})
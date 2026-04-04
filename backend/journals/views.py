# journals/views.py

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
    question = request.data.get("question", "")
    answer = request.data.get("answer", "")

    if not journal_id:
        return Response({"saved": False, "reason": "no journal_id"})

    try:
        journal = Journal.objects.get(id=journal_id, user=request.user)
        journal.reflection_question = question
        journal.reflection_answer = answer
        journal.save()
        return Response({"saved": True})
    except Journal.DoesNotExist:
        return Response({"saved": False, "reason": "not found"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_reflection_question(request):
    journal_text = request.data.get("journal_text", "")
    dominant_emotion = request.data.get("dominant_emotion", "neutral")

    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

    if not GROQ_API_KEY:
        return Response({"question": "What felt most significant about what you wrote?"})

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "max_tokens": 80,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a warm, empathetic journaling companion. "
                            "Generate exactly ONE short follow-up question based on the user's journal entry. "
                            "The question should: acknowledge what they actually wrote about specifically, "
                            "invite them to reflect one layer deeper, feel like it came from a caring friend not a therapist, "
                            "be under 20 words, NOT mention the emotion label directly, NOT start with 'I'. "
                            "Return only the question, nothing else."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f'Journal entry: "{journal_text}"\nDetected emotion: {dominant_emotion}',
                    },
                ],
            },
            timeout=10,
        )
        data = response.json()
        question = data["choices"][0]["message"]["content"].strip()
        return Response({"question": question})

    except Exception as e:
        logger.error(f"Groq question generation failed: {str(e)}")
        return Response({"question": "What felt most significant about what you wrote?"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_reflection_closing(request):
    journal_text = request.data.get("journal_text", "")
    question = request.data.get("question", "")
    answer = request.data.get("answer", "")

    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

    if not GROQ_API_KEY:
        return Response({"closing": "Thank you for going deeper. That took courage."})

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "max_tokens": 60,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a warm, empathetic journaling companion. "
                            "The user answered a reflection question. Generate ONE short warm closing response that: "
                            "acknowledges what they said warmly and specifically, does NOT ask another question, "
                            "feels like a gentle human close, is under 20 words. "
                            "Return only the response, nothing else."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f'Original journal: "{journal_text}"\nQuestion: "{question}"\nAnswer: "{answer}"',
                    },
                ],
            },
            timeout=10,
        )
        data = response.json()
        closing = data["choices"][0]["message"]["content"].strip()
        return Response({"closing": closing})

    except Exception as e:
        logger.error(f"Groq closing generation failed: {str(e)}")
        return Response({"closing": "Thank you for going deeper. That took courage."})
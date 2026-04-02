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

    journal = Journal.objects.create(
        user=request.user,
        text=text
    )

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
        "journal_text": text,
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
            "weekly_confidence": analytics.get("weekly_confidence", 0.0)
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
            "has_reflection": bool(j.reflection_answer),
        }
        for j in journals
    ]

    return Response(data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def save_reflection(request):
    journal_id = request.data.get("journal_id")
    question = request.data.get("question")
    answer = request.data.get("answer")

    if not journal_id or not question or not answer:
        raise ValidationError("journal_id, question and answer are required")

    try:
        journal = Journal.objects.get(id=journal_id, user=request.user)
        journal.reflection_question = question
        journal.reflection_answer = answer
        journal.save()
        logger.info(f"Reflection saved for journal {journal_id}")
        return Response({"success": True})
    except Journal.DoesNotExist:
        raise ValidationError("Journal not found")
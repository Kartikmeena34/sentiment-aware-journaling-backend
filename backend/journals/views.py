# journals/views.py

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError

from .models import Journal
from .services.emotion_service import detect_emotion
from .services.analytics_service import compute_user_analytics
from .services.pet_service import get_pet_state
from .services.insight_service import generate_insight

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

    # Save journal immediately
    journal = Journal.objects.create(
        user=request.user,
        text=text
    )

    logger.info(f"Journal {journal.id} saved (initial save)")

    # Attempt emotion detection
    try:
        emotion_data = detect_emotion(text)

        journal.emotion_data = emotion_data["raw"]
        journal.dominant_emotion = emotion_data["dominant_emotion"]
        journal.confidence = emotion_data["confidence"]
        journal.save()

    except Exception as e:
        logger.error(f"Emotion detection failed for journal {journal.id}: {str(e)}")

    analytics = compute_user_analytics(request.user)
    pet = get_pet_state(analytics.get("weekly_distribution", {}))
    insight = generate_insight(analytics)

    return Response({
        "journal_id": journal.id,
        "dominant_emotion": journal.dominant_emotion,
        "confidence": journal.confidence,
        "analytics": analytics,
        "pet": pet,
        "insight": insight
    })


class UserAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        logger.info(f"Analytics requested by user {request.user.username}")
        analytics = compute_user_analytics(request.user)
        return Response(analytics)
    
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
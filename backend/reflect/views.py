# reflect/views.py

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework import status

from .models import ReflectSession, ReflectMessage
from .services.claude_service import get_opening_question, get_next_question
from journals.services.emotion_service import detect_emotion

import logging
logger = logging.getLogger(__name__)


def _detect_emotional_arc(session):
    """
    Analyse the emotional journey across a completed reflect session.
    Returns arc_type and a list of arc data points.
    """
    user_messages = list(
        session.messages.filter(
            role='user',
            dominant_emotion__isnull=False
        ).order_by('created_at')
    )

    if len(user_messages) < 2:
        return None, []

    arc_points = [
        {
            "index": i,
            "emotion": msg.dominant_emotion,
            "confidence": msg.confidence or 0.0,
        }
        for i, msg in enumerate(user_messages)
    ]

    first_emotion = user_messages[0].dominant_emotion
    last_emotion = user_messages[-1].dominant_emotion

    negative = {'sadness', 'fear', 'anger', 'disgust'}
    positive = {'joy', 'surprise'}
    neutral = {'neutral'}

    if first_emotion in negative and last_emotion in (positive | neutral):
        arc_type = 'resolution'
    elif first_emotion in (neutral | positive) and last_emotion in negative:
        arc_type = 'deepening'
    elif first_emotion == last_emotion:
        arc_type = 'stable'
    else:
        arc_type = 'shifting'

    return arc_type, arc_points


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def start_session(request):
    """
    Start a new reflect session.
    Creates the session, generates the opening question, saves it as
    the first assistant message, and returns session_id + question.
    """
    # Check if user already has an incomplete session
    existing = ReflectSession.objects.filter(
        user=request.user,
        is_complete=False
    ).first()

    if existing:
        # Return the existing session's last question
        last_assistant = existing.messages.filter(
            role='assistant'
        ).last()
        question = last_assistant.content if last_assistant else get_opening_question()
        return Response({
            "session_id": existing.id,
            "question": question,
            "resumed": True,
        })

    # Create new session
    session = ReflectSession.objects.create(user=request.user)

    entry_count = request.user.journals.count()
    question = get_opening_question(entry_count)

    ReflectMessage.objects.create(
        session=session,
        role='assistant',
        content=question,
    )

    logger.info(f"Reflect session {session.id} started for {request.user.username}")

    return Response({
        "session_id": session.id,
        "question": question,
        "resumed": False,
    }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def send_message(request):
    """
    Send a user message, run emotion detection on it, then get the
    next question from Claude.

    Body: { "session_id": int, "content": str }
    """
    session_id = request.data.get("session_id")
    content = request.data.get("content", "").strip()

    if not session_id:
        raise ValidationError("session_id is required")
    if not content:
        raise ValidationError("content is required")
    if len(content) > 2000:
        raise ValidationError("Message exceeds 2000 characters")

    try:
        session = ReflectSession.objects.get(
            id=session_id,
            user=request.user,
            is_complete=False,
        )
    except ReflectSession.DoesNotExist:
        raise NotFound("Session not found or already complete")

    # Save user message
    user_msg = ReflectMessage.objects.create(
        session=session,
        role='user',
        content=content,
    )

    # Run emotion detection on user message (best-effort)
    try:
        emotion_result = detect_emotion(content)
        user_msg.emotion_data = emotion_result["raw"]
        user_msg.dominant_emotion = emotion_result["dominant_emotion"]
        user_msg.confidence = emotion_result["confidence"]
        user_msg.save()
    except Exception as e:
        logger.warning(f"Emotion detection failed for reflect message {user_msg.id}: {e}")

    # Get full conversation history and generate next question
    history = list(session.messages.order_by('created_at'))
    next_question = get_next_question(history)

    assistant_msg = ReflectMessage.objects.create(
        session=session,
        role='assistant',
        content=next_question,
    )

    logger.info(
        f"Reflect message exchange in session {session.id}: "
        f"user emotion={user_msg.dominant_emotion}"
    )

    return Response({
        "question": next_question,
        "message_id": user_msg.id,
        "dominant_emotion": user_msg.dominant_emotion,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def end_session(request):
    """
    End a reflect session.
    Detects emotional arc, computes dominant emotion across the session,
    marks session complete.

    Body: { "session_id": int }
    """
    session_id = request.data.get("session_id")

    if not session_id:
        raise ValidationError("session_id is required")

    try:
        session = ReflectSession.objects.get(
            id=session_id,
            user=request.user,
            is_complete=False,
        )
    except ReflectSession.DoesNotExist:
        raise NotFound("Session not found or already complete")

    # Detect emotional arc
    arc_type, arc_points = _detect_emotional_arc(session)

    # Compute dominant emotion for the session
    user_messages = list(
        session.messages.filter(
            role='user',
            dominant_emotion__isnull=False
        )
    )

    dominant_emotion = None
    confidence = None

    if user_messages:
        emotion_counts = {}
        for msg in user_messages:
            e = msg.dominant_emotion
            emotion_counts[e] = emotion_counts.get(e, 0) + (msg.confidence or 0.5)
        dominant_emotion = max(emotion_counts, key=emotion_counts.get)
        confidence = round(
            sum(m.confidence or 0 for m in user_messages) / len(user_messages), 3
        )

    # Save and close session
    session.dominant_emotion = dominant_emotion
    session.confidence = confidence
    session.emotional_arc = arc_points
    session.arc_type = arc_type
    session.is_complete = True
    session.save()

    logger.info(
        f"Reflect session {session.id} ended: arc={arc_type}, "
        f"dominant={dominant_emotion}"
    )

    # Build arc summary for frontend
    arc_summary = None
    if arc_type and len(arc_points) >= 2:
        from_emotion = arc_points[0]['emotion']
        to_emotion = arc_points[-1]['emotion']
        arc_labels = {
            'resolution': f"You moved from {from_emotion} to {to_emotion} across this reflection.",
            'deepening': f"Your feelings deepened from {from_emotion} to {to_emotion} through this conversation.",
            'stable': f"You stayed with {from_emotion} throughout — that kind of consistency says something.",
            'shifting': f"Your emotions shifted from {from_emotion} to {to_emotion} as you reflected.",
        }
        arc_summary = arc_labels.get(arc_type)

    return Response({
        "session_id": session.id,
        "dominant_emotion": dominant_emotion,
        "arc_type": arc_type,
        "arc_summary": arc_summary,
        "message_count": len(user_messages),
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def session_history(request):
    """
    Return all completed reflect sessions for the user,
    most recent first. Includes message count and arc data.
    """
    sessions = (
        ReflectSession.objects
        .filter(user=request.user, is_complete=True)
        .prefetch_related('messages')
        .order_by('-created_at')
    )

    data = []
    for session in sessions:
        user_messages = [m for m in session.messages.all() if m.role == 'user']
        preview = user_messages[0].content[:120] if user_messages else ""

        data.append({
            "id": session.id,
            "created_at": session.created_at,
            "dominant_emotion": session.dominant_emotion,
            "confidence": session.confidence,
            "arc_type": session.arc_type,
            "arc_summary": _build_arc_summary(session),
            "message_count": len(user_messages),
            "preview": preview,
        })

    return Response(data)


def _build_arc_summary(session):
    """Helper to rebuild arc summary string from stored data."""
    if not session.arc_type or not session.emotional_arc or len(session.emotional_arc) < 2:
        return None

    from_emotion = session.emotional_arc[0]['emotion']
    to_emotion = session.emotional_arc[-1]['emotion']

    arc_labels = {
        'resolution': f"{from_emotion.capitalize()} → {to_emotion.capitalize()}",
        'deepening': f"{from_emotion.capitalize()} → {to_emotion.capitalize()}",
        'stable': f"Steady {from_emotion}",
        'shifting': f"{from_emotion.capitalize()} → {to_emotion.capitalize()}",
    }
    return arc_labels.get(session.arc_type)
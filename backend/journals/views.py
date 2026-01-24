import requests
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.contrib.auth.models import User
from .models import JournalEntry
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import permission_classes


FASTAPI_URL = "http://127.0.0.1:8001/predict"

@api_view(["POST"])
@permission_classes([IsAuthenticated])


def create_journal(request):
    text = request.data.get("text")

    user = request.user


    entry = JournalEntry.objects.create(
        user=user,
        text=text
    )

    try:
        r = requests.post(FASTAPI_URL, json={"text": text}, timeout=5)
        entry.emotions = r.json()
        entry.save()
    except Exception:
        pass

    return Response({
        "id": entry.id,
        "text": entry.text,
        "emotions": entry.emotions
    })

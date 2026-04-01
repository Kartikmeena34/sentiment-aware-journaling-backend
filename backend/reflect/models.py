from django.db import models
from django.contrib.auth.models import User


class ReflectSession(models.Model):
    """
    A single guided reflection conversation session.
    Stores the full emotional arc detected across the conversation.
    """
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="reflect_sessions"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Populated when session ends
    dominant_emotion = models.CharField(max_length=50, null=True, blank=True)
    confidence = models.FloatField(null=True, blank=True)

    # JSON: [{"index": 0, "emotion": "fear", "confidence": 0.8}, ...]
    emotional_arc = models.JSONField(null=True, blank=True)

    # arc_type: "resolution" | "deepening" | "stable" | "shifting" | None
    arc_type = models.CharField(max_length=50, null=True, blank=True)

    is_complete = models.BooleanField(default=False)

    def __str__(self):
        return f"ReflectSession {self.id} by {self.user.username} ({'complete' if self.is_complete else 'active'})"


class ReflectMessage(models.Model):
    """
    A single message within a ReflectSession.
    role: 'assistant' (Claude's question) or 'user' (user's response)
    """
    ROLE_CHOICES = [
        ('assistant', 'Assistant'),
        ('user', 'User'),
    ]

    session = models.ForeignKey(
        ReflectSession, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    # Only populated for role='user' messages after emotion detection
    emotion_data = models.JSONField(null=True, blank=True)
    dominant_emotion = models.CharField(max_length=50, null=True, blank=True)
    confidence = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.role}] Session {self.session_id}: {self.content[:50]}"
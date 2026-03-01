from django.db import models
from django.contrib.auth.models import User

class Journal(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="journals"
    )
    text = models.TextField()
    emotion_data = models.JSONField(null=True, blank=True)
    dominant_emotion = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Journal {self.id} by {self.user.username}"
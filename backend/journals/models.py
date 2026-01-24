from django.db import models
from django.contrib.auth.models import User

class JournalEntry(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="journals"
    )
    text = models.TextField()
    emotions = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Journal {self.id} by {self.user.username}"

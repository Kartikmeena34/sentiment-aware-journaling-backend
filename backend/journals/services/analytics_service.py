# journals/services/analytics_service.py

from django.utils import timezone
from datetime import timedelta
from collections import Counter
from ..models import Journal

def compute_user_analytics(user):
    one_week_ago = timezone.now() - timedelta(days=7)

    journals = Journal.objects.filter(
        user = user,
        created_at__gte= one_week_ago
    ).order_by("created_at")

    if not journals.exists():
        return{
            "weekly_distribution": {},
            "stability_score":0.0,
            "trend":{}
        }
    
# extract dominant emotion from json field

    emotions= [
        j.dominant_emotion
        for j in journals
        if j.dominant_emotion
    ]

# --weekly distribution--
    distribution = dict(Counter(emotions))

# --stability score--
    stability_score = calculate_stability_score(emotions)

# --trend analysis--
    trend = detect_trends(emotions)

    return {
        "weekly_distribution": distribution,
        "stability_score": stability_score,
        "trends": trend
    }

# pending to understand
def calculate_stability_score(emotions):
    if len(emotions)<=1:
        return 1.0
    
    changes = 0
    for i in range(1, len(emotions)):
        if emotions[i] != emotions[i-1]:
            changes += 1

    stability = 1-(changes/(len(emotions)-1))
    return round(stability, 2)

def detect_trends(emotions):
    if len(emotions)<4:
        return {}
    
    midpoint = len(emotions)//2
    earlier= emotions[:midpoint]
    recent= emotions[midpoint:]

    earlier_counts = Counter(earlier)
    recent_counts = Counter(recent)

    trend = {}

    all_emotions = set(earlier_counts.keys())| set(recent_counts.keys()) 

    for emotion in all_emotions:
        diff = recent_counts.get(emotion, 0) - earlier_counts.get(emotion, 0)

        if diff > 0:
            trend[emotion] = "increasing"
        elif diff < 0:
            trend[emotion] = "decreasing"

    return trend


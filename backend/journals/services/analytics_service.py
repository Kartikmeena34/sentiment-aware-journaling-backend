import math
from django.utils import timezone
from datetime import timedelta
from ..models import Journal


def calculate_entropy(distribution):
    total = sum(distribution.values())
    if total == 0:
        return 0.0

    entropy = 0.0
    for p in distribution.values():
        if p > 0:
            entropy -= p * math.log2(p)

    return round(entropy, 3)


def compute_weighted_distribution(journals):
    aggregate = {}
    total_confidence = 0.0
    valid_entries = 0

    for journal in journals:
        emotion_probs = journal.emotion_data
        confidence = journal.confidence or 0.0

        if not emotion_probs or confidence == 0.0:
            continue

        valid_entries += 1
        total_confidence += confidence

        for emotion, score in emotion_probs.items():
            weighted_score = score * confidence
            aggregate[emotion] = aggregate.get(emotion, 0) + weighted_score

    if total_confidence == 0:
        return {}, 0, 0.0

    averaged_distribution = {
        emotion: round(score / total_confidence, 3)
        for emotion, score in aggregate.items()
    }

    avg_weekly_confidence = round(total_confidence / valid_entries, 3)

    return averaged_distribution, valid_entries, avg_weekly_confidence


def detect_weighted_trends(journals):
    if len(journals) < 4:
        return {}

    # Prepare per-emotion time series
    emotion_series = {}

    for idx, journal in enumerate(journals):
        emotion_probs = journal.emotion_data
        confidence = journal.confidence or 0.0

        if not emotion_probs or confidence == 0.0:
            continue

        for emotion, score in emotion_probs.items():
            weighted_score = score * confidence
            emotion_series.setdefault(emotion, []).append((idx, weighted_score))

    trends = {}

    for emotion, points in emotion_series.items():
        if len(points) < 3:
            continue

        x_vals = [p[0] for p in points]
        y_vals = [p[1] for p in points]

        n = len(points)

        sum_x = sum(x_vals)
        sum_y = sum(y_vals)
        sum_xy = sum(x * y for x, y in zip(x_vals, y_vals))
        sum_x2 = sum(x * x for x in x_vals)

        denominator = (n * sum_x2 - sum_x ** 2)
        if denominator == 0:
            continue

        slope = (n * sum_xy - sum_x * sum_y) / denominator

        # Threshold for meaningful slope
        if slope > 0.02:
            trends[emotion] = "increasing"
        elif slope < -0.02:
            trends[emotion] = "decreasing"

    return trends

def compute_user_analytics(user):
    one_week_ago = timezone.now() - timedelta(days=7)

    journals = list(
        Journal.objects.filter(
            user=user,
            created_at__gte=one_week_ago
        ).order_by("created_at")
    )

    distribution, valid_entries, weekly_confidence = compute_weighted_distribution(journals)

    if valid_entries < 3:
        return {
            "weekly_distribution": {},
            "emotional_entropy": None,
            "trends": {},
            "data_sufficiency": False,
            "weekly_confidence": 0.0,
        }

    entropy = calculate_entropy(distribution)

    trend = {}
    if valid_entries >= 4:
        trend = detect_weighted_trends(journals)

    return {
        "weekly_distribution": distribution,
        "emotional_entropy": entropy,
        "trends": trend,
        "data_sufficiency": True,
        "weekly_confidence": weekly_confidence,
    }
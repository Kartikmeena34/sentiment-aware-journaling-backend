# analytics_service.py
import math
from django.utils import timezone
from datetime import timedelta
from ..models import Journal


def calculate_entropy(distribution):
    """
    Calculate Shannon entropy of emotion distribution.
    Higher entropy = more diverse emotions.
    """
    total = sum(distribution.values())
    if total == 0:
        return 0.0

    entropy = 0.0
    for p in distribution.values():
        if p > 0:
            entropy -= p * math.log2(p)

    return round(entropy, 3)


def compute_weighted_distribution(journals):
    """
    Aggregate emotion scores across journals, weighted by confidence.
    Returns normalized distribution, entry count, and average confidence.
    """
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
    """
    Detect increasing/decreasing trends for each emotion using linear regression.
    Requires at least 4 journals with valid emotion data.
    """
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


def compute_baseline(user, days=30):
    """
    Calculate user's baseline emotional state over the last N days.
    Returns average distribution and count of valid entries.
    """
    cutoff_date = timezone.now() - timedelta(days=days)
    
    journals = list(
        Journal.objects.filter(
            user=user,
            created_at__gte=cutoff_date
        ).order_by("created_at")
    )
    
    if len(journals) < 7:  # Need at least a week of data for baseline
        return None, 0
    
    distribution, valid_entries, avg_confidence = compute_weighted_distribution(journals)
    
    return distribution, valid_entries


def calculate_baseline_shift(current_distribution, baseline_distribution):
    """
    Compare current week to baseline.
    Returns shift magnitude and direction for emotions with significant changes.
    """
    if not baseline_distribution or not current_distribution:
        return {}
    
    shifts = {}
    
    # Check all emotions that appear in either distribution
    all_emotions = set(list(current_distribution.keys()) + list(baseline_distribution.keys()))
    
    for emotion in all_emotions:
        current_val = current_distribution.get(emotion, 0)
        baseline_val = baseline_distribution.get(emotion, 0)
        
        if baseline_val == 0:
            continue
        
        # Calculate percentage change
        change = (current_val - baseline_val) / baseline_val
        
        # Only report significant shifts (>20% change)
        if abs(change) > 0.20:
            shifts[emotion] = {
                "change": round(change, 2),
                "direction": "increased" if change > 0 else "decreased",
                "magnitude": abs(round(change * 100))  # Convert to percentage
            }
    
    return shifts


def detect_emotional_range_trend(user):
    """
    Compare emotional entropy (range) over time.
    Returns whether range is expanding, contracting, or stable.
    """
    thirty_days_ago = timezone.now() - timedelta(days=30)
    seven_days_ago = timezone.now() - timedelta(days=7)
    
    # Last 7 days
    recent_journals = list(
        Journal.objects.filter(
            user=user,
            created_at__gte=seven_days_ago
        ).order_by("created_at")
    )
    
    # Previous 23 days (for comparison)
    older_journals = list(
        Journal.objects.filter(
            user=user,
            created_at__gte=thirty_days_ago,
            created_at__lt=seven_days_ago
        ).order_by("created_at")
    )
    
    if len(recent_journals) < 3 or len(older_journals) < 3:
        return None
    
    recent_dist, _, _ = compute_weighted_distribution(recent_journals)
    older_dist, _, _ = compute_weighted_distribution(older_journals)
    
    recent_entropy = calculate_entropy(recent_dist)
    older_entropy = calculate_entropy(older_dist)
    
    if older_entropy == 0:
        return None
    
    change = (recent_entropy - older_entropy) / older_entropy
    
    if change > 0.15:
        return {"trend": "expanding", "change": round(change, 2)}
    elif change < -0.15:
        return {"trend": "contracting", "change": round(change, 2)}
    else:
        return {"trend": "stable", "change": round(change, 2)}


def compute_user_analytics(user):
    """
    Enhanced analytics with baseline comparison and range trend detection.
    Returns comprehensive emotional analytics for the user.
    """
    one_week_ago = timezone.now() - timedelta(days=7)
    
    # Current week data
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
            "baseline_shifts": {},
            "range_trend": None,
        }
    
    entropy = calculate_entropy(distribution)
    
    # Trend detection within current week
    trend = {}
    if valid_entries >= 4:
        trend = detect_weighted_trends(journals)
    
    # Baseline comparison (30-day average vs current week)
    baseline_dist, baseline_entries = compute_baseline(user, days=30)
    baseline_shifts = {}
    if baseline_dist and baseline_entries >= 7:
        baseline_shifts = calculate_baseline_shift(distribution, baseline_dist)
    
    # Emotional range trend (expanding vs contracting)
    range_trend = detect_emotional_range_trend(user)
    
    return {
        "weekly_distribution": distribution,
        "emotional_entropy": entropy,
        "trends": trend,
        "data_sufficiency": True,
        "weekly_confidence": weekly_confidence,
        "baseline_shifts": baseline_shifts,
        "range_trend": range_trend,
    }
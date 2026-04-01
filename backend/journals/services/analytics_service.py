# analytics_service.py
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
        if slope > 0.02:
            trends[emotion] = "increasing"
        elif slope < -0.02:
            trends[emotion] = "decreasing"

    return trends


def compute_baseline(user, days=30):
    """
    Adaptive baseline window:
    - < 14 days active  → 7-day window (min 3 entries)
    - < 30 days active  → 14-day window (min 5 entries)
    - >= 30 days active → 30-day window (min 7 entries)
    """
    first_entry = (
        Journal.objects.filter(user=user).order_by("created_at").first()
    )
    if not first_entry:
        return None, 0

    days_active = (timezone.now() - first_entry.created_at).days

    if days_active < 14:
        window_days, min_entries = 7, 3
    elif days_active < 30:
        window_days, min_entries = 14, 5
    else:
        window_days, min_entries = days, 7

    cutoff_date = timezone.now() - timedelta(days=window_days)
    journals = list(
        Journal.objects.filter(
            user=user, created_at__gte=cutoff_date
        ).order_by("created_at")
    )

    if len(journals) < min_entries:
        return None, 0

    distribution, valid_entries, _ = compute_weighted_distribution(journals)
    return distribution, valid_entries


def calculate_baseline_shift(current_distribution, baseline_distribution):
    if not baseline_distribution or not current_distribution:
        return {}

    shifts = {}
    all_emotions = set(
        list(current_distribution.keys()) + list(baseline_distribution.keys())
    )

    for emotion in all_emotions:
        current_val = current_distribution.get(emotion, 0)
        baseline_val = baseline_distribution.get(emotion, 0)
        if baseline_val == 0:
            continue
        change = (current_val - baseline_val) / baseline_val
        if abs(change) > 0.20:
            shifts[emotion] = {
                "change": round(change, 2),
                "direction": "increased" if change > 0 else "decreased",
                "magnitude": abs(round(change * 100)),
            }

    return shifts


def detect_emotional_range_trend(user):
    thirty_days_ago = timezone.now() - timedelta(days=30)
    seven_days_ago = timezone.now() - timedelta(days=7)

    recent_journals = list(
        Journal.objects.filter(
            user=user, created_at__gte=seven_days_ago
        ).order_by("created_at")
    )
    older_journals = list(
        Journal.objects.filter(
            user=user,
            created_at__gte=thirty_days_ago,
            created_at__lt=seven_days_ago,
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


def detect_crisis(user):
    """
    Triggers when BOTH are true in the last 7 days:
    1. Combined sadness + fear weighted score > 0.65
    2. 4+ entries with sadness or fear as dominant emotion
    """
    seven_days_ago = timezone.now() - timedelta(days=7)

    journals = list(
        Journal.objects.filter(
            user=user,
            created_at__gte=seven_days_ago,
            emotion_data__isnull=False,
            confidence__isnull=False,
        ).order_by("created_at")
    )

    if len(journals) < 4:
        return False

    distribution, valid_entries, _ = compute_weighted_distribution(journals)
    if valid_entries == 0:
        return False

    combined_score = distribution.get("sadness", 0) + distribution.get("fear", 0)
    if combined_score <= 0.65:
        return False

    distress_count = sum(
        1 for j in journals if j.dominant_emotion in ("sadness", "fear")
    )
    return distress_count >= 4


# ─────────────────────────────────────────────────────────────
# TWO-STREAM REFLECT ANALYTICS
# ─────────────────────────────────────────────────────────────

def compute_reflect_analytics(user):
    """
    Pull analytics from completed ReflectSessions in the last 7 days.
    Returns reflect-specific data: session count, arc types, divergence signal.
    """
    try:
        from reflect.models import ReflectSession, ReflectMessage
    except ImportError:
        return {}

    seven_days_ago = timezone.now() - timedelta(days=7)

    sessions = list(
        ReflectSession.objects.filter(
            user=user,
            is_complete=True,
            created_at__gte=seven_days_ago,
        ).prefetch_related('messages')
    )

    if not sessions:
        return {"reflect_session_count": 0}

    # Aggregate emotion distribution from reflect user messages
    reflect_messages = []
    for session in sessions:
        reflect_messages.extend([
            m for m in session.messages.all()
            if m.role == 'user' and m.emotion_data and m.confidence
        ])

    # Build a lightweight journal-like object for reuse
    class _MsgProxy:
        def __init__(self, msg):
            self.emotion_data = msg.emotion_data
            self.confidence = msg.confidence
            self.dominant_emotion = msg.dominant_emotion

    proxies = [_MsgProxy(m) for m in reflect_messages]
    reflect_dist, _, reflect_confidence = compute_weighted_distribution(proxies)

    # Arc summary: most common arc type this week
    arc_types = [s.arc_type for s in sessions if s.arc_type]
    most_common_arc = max(set(arc_types), key=arc_types.count) if arc_types else None

    return {
        "reflect_session_count": len(sessions),
        "reflect_distribution": reflect_dist,
        "reflect_confidence": reflect_confidence,
        "most_common_arc": most_common_arc,
    }


def compute_divergence(journal_dist, reflect_dist):
    """
    Compare journal and reflect emotion distributions.
    Returns the emotion that diverges most between the two modes,
    and the direction of divergence.
    """
    if not journal_dist or not reflect_dist:
        return None

    all_emotions = set(list(journal_dist.keys()) + list(reflect_dist.keys()))
    max_diff = 0
    divergent_emotion = None
    direction = None

    for emotion in all_emotions:
        j_val = journal_dist.get(emotion, 0)
        r_val = reflect_dist.get(emotion, 0)
        diff = abs(j_val - r_val)
        if diff > max_diff and diff > 0.15:  # only meaningful divergence
            max_diff = diff
            divergent_emotion = emotion
            direction = "reflect" if r_val > j_val else "journal"

    if not divergent_emotion:
        return None

    return {
        "emotion": divergent_emotion,
        "dominant_in": direction,
        "difference": round(max_diff, 2),
    }


def compute_user_analytics(user):
    """
    Full analytics pipeline — journal stream + reflect stream.
    """
    one_week_ago = timezone.now() - timedelta(days=7)

    journals = list(
        Journal.objects.filter(
            user=user, created_at__gte=one_week_ago
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
            "crisis_flag": False,
            "reflect": {"reflect_session_count": 0},
            "divergence": None,
        }

    entropy = calculate_entropy(distribution)

    trend = {}
    if valid_entries >= 4:
        trend = detect_weighted_trends(journals)

    baseline_dist, baseline_entries = compute_baseline(user, days=30)
    baseline_shifts = {}
    if baseline_dist and baseline_entries >= 3:
        baseline_shifts = calculate_baseline_shift(distribution, baseline_dist)

    range_trend = detect_emotional_range_trend(user)
    crisis_flag = detect_crisis(user)

    # Reflect stream
    reflect_data = compute_reflect_analytics(user)
    divergence = compute_divergence(
        distribution, reflect_data.get("reflect_distribution", {})
    )

    return {
        "weekly_distribution": distribution,
        "emotional_entropy": entropy,
        "trends": trend,
        "data_sufficiency": True,
        "weekly_confidence": weekly_confidence,
        "baseline_shifts": baseline_shifts,
        "range_trend": range_trend,
        "crisis_flag": crisis_flag,
        "reflect": reflect_data,
        "divergence": divergence,
    }
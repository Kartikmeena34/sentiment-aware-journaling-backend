# insight_service.py

def generate_insight(analytics):
    """Single insight — highest priority signal wins."""
    weekly_confidence = analytics.get("weekly_confidence", 0.0)
    distribution = analytics.get("weekly_distribution", {})
    entropy = analytics.get("emotional_entropy")
    trends = analytics.get("trends", {})
    sufficient = analytics.get("data_sufficiency", False)
    baseline_shifts = analytics.get("baseline_shifts", {})
    range_trend = analytics.get("range_trend")

    if not sufficient:
        return "Keep journaling to unlock insights. We need at least 3 entries from this week."

    if not distribution:
        return "Your entries this week didn't contain clear emotional signals. Try writing more about how you're feeling."

    if baseline_shifts:
        largest_shift = max(baseline_shifts.items(), key=lambda x: x[1]["magnitude"])
        emotion, shift_data = largest_shift
        direction = shift_data["direction"]
        magnitude = shift_data["magnitude"]
        qualifier = "It seems " if weekly_confidence < 0.6 else ""
        message = (
            f"{qualifier}Your {emotion.lower()} has {direction} by {magnitude}% "
            f"compared to your usual baseline over the last month."
        )
        if len(baseline_shifts) > 1:
            others = [e for e in baseline_shifts.keys() if e != emotion]
            if others:
                message += f" Your {others[0].lower()} also shifted noticeably."
        return message

    if range_trend and range_trend["trend"] != "stable":
        if range_trend["trend"] == "expanding":
            return "Your emotional range is expanding — you're expressing more diverse feelings lately."
        else:
            return "Your emotional range is narrowing — your recent entries show less emotional variety than before."

    if trends:
        emotion, direction = list(trends.items())[0]
        if direction == "increasing":
            return f"Your {emotion.lower()} appears to be building up over the course of this week."
        else:
            return f"Your {emotion.lower()} seems to be declining as the week progresses."

    if entropy and entropy >= 2.0:
        return "You experienced a wide range of emotions this week — your entries reflect significant emotional variety."

    dominant = max(distribution, key=distribution.get)
    dominant_score = distribution[dominant]

    if dominant_score > 0.5:
        return f"Your entries this week were most often characterized by {dominant.lower()}."
    return "Your entries this week showed a balanced mix of emotions."


def generate_multiple_insights(analytics):
    """
    Generate up to 5 distinct insight cards.
    Includes reflect-stream insights when data is available.
    """
    insights = []

    weekly_confidence = analytics.get("weekly_confidence", 0.0)
    distribution = analytics.get("weekly_distribution", {})
    entropy = analytics.get("emotional_entropy")
    trends = analytics.get("trends", {})
    sufficient = analytics.get("data_sufficiency", False)
    baseline_shifts = analytics.get("baseline_shifts", {})
    range_trend = analytics.get("range_trend")
    reflect_data = analytics.get("reflect", {})
    divergence = analytics.get("divergence")

    if not sufficient:
        return [{
            "type": "insufficient_data",
            "title": "Not Enough Data Yet",
            "message": "Keep journaling to unlock insights. We need at least 3 entries from this week.",
            "confidence": 0.0,
        }]

    # ── 1. Baseline Shift ──
    if baseline_shifts:
        largest_shift = max(baseline_shifts.items(), key=lambda x: x[1]["magnitude"])
        emotion, shift_data = largest_shift
        insights.append({
            "type": "baseline_shift",
            "title": f"{emotion.capitalize()} Has {shift_data['direction'].capitalize()}",
            "message": (
                f"Your {emotion.lower()} has {shift_data['direction']} by "
                f"{shift_data['magnitude']}% compared to your usual baseline."
            ),
            "confidence": weekly_confidence,
        })

    # ── 2. Emotional Range Trend ──
    if range_trend and range_trend["trend"] != "stable":
        if range_trend["trend"] == "expanding":
            insights.append({
                "type": "range_expanding",
                "title": "Emotional Range Expanding",
                "message": "You're expressing more diverse feelings in your entries lately.",
                "confidence": weekly_confidence,
            })
        else:
            insights.append({
                "type": "range_contracting",
                "title": "Emotional Range Narrowing",
                "message": "Your recent entries show less emotional variety than before.",
                "confidence": weekly_confidence,
            })

    # ── 3. Within-Week Trend ──
    if trends and len(insights) < 4:
        for emotion, direction in list(trends.items())[:1]:
            label = "Building Up" if direction == "increasing" else "Declining"
            verb = "increasing" if direction == "increasing" else "decreasing"
            insights.append({
                "type": f"trend_{direction}",
                "title": f"{emotion.capitalize()} {label}",
                "message": f"Your {emotion.lower()} appears to be {verb} over the course of this week.",
                "confidence": weekly_confidence,
            })

    # ── 4. Reflect Divergence (two-stream insight) ──
    if divergence and len(insights) < 4:
        emotion = divergence["emotion"]
        dominant_in = divergence["dominant_in"]
        insights.append({
            "type": "reflect_divergence",
            "title": f"More {emotion.capitalize()} in Your Reflections",
            "message": (
                f"Your guided reflections surface more {emotion.lower()} than your "
                f"free-form journals this week — suggesting there's more beneath the surface."
                if dominant_in == "reflect"
                else
                f"Your journals carry more {emotion.lower()} than your reflections — "
                f"you may be processing it differently in each mode."
            ),
            "confidence": weekly_confidence,
        })

    # ── 5. Reflect Arc Insight ──
    arc = reflect_data.get("most_common_arc")
    session_count = reflect_data.get("reflect_session_count", 0)
    if arc and session_count >= 1 and len(insights) < 5:
        arc_messages = {
            "resolution": "Your recent reflections tend to move toward calm — you're working through things.",
            "deepening": "Your reflections often move deeper into emotion as you explore. That takes courage.",
            "stable": "You've been sitting with consistent feelings across your reflections this week.",
            "shifting": "Your emotions shift noticeably during reflection — your thinking is actively evolving.",
        }
        if arc in arc_messages:
            insights.append({
                "type": "reflect_arc",
                "title": "Reflection Pattern",
                "message": arc_messages[arc],
                "confidence": weekly_confidence,
            })

    # ── Fallback: High Entropy ──
    if not insights and entropy and entropy >= 2.0:
        insights.append({
            "type": "high_diversity",
            "title": "Wide Emotional Range",
            "message": "You experienced significant emotional variety this week.",
            "confidence": weekly_confidence,
        })

    # ── Final Fallback ──
    if not insights:
        dominant = max(distribution, key=distribution.get) if distribution else "neutral"
        insights.append({
            "type": "weekly_summary",
            "title": "This Week's Snapshot",
            "message": f"Your entries this week were most often characterized by {dominant.lower()}.",
            "confidence": weekly_confidence,
        })

    return insights
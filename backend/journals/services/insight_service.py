def generate_insight(analytics):
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
        confidence_qualifier = "It seems " if weekly_confidence < 0.6 else ""
        baseline_message = (
            f"{confidence_qualifier}Your {emotion.lower()} has {direction} by {magnitude}% "
            f"compared to your usual baseline over the last month."
        )
        if len(baseline_shifts) > 1:
            other_shifts = [e for e in baseline_shifts.keys() if e != emotion]
            if other_shifts:
                baseline_message += f" Your {other_shifts[0].lower()} also shifted noticeably."
        return baseline_message

    if range_trend and range_trend["trend"] != "stable":
        trend_type = range_trend["trend"]
        if trend_type == "expanding":
            return "Your emotional range is expanding — you're expressing more diverse feelings in your entries lately."
        elif trend_type == "contracting":
            return "Your emotional range is narrowing — your recent entries show less emotional variety than before."

    if trends:
        strongest_trend = list(trends.items())[0]
        emotion, direction = strongest_trend
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
    else:
        return "Your entries this week showed a balanced mix of emotions."


def generate_multiple_insights(analytics):
    insights = []

    weekly_confidence = analytics.get("weekly_confidence", 0.0)
    distribution = analytics.get("weekly_distribution", {})
    entropy = analytics.get("emotional_entropy")
    trends = analytics.get("trends", {})
    sufficient = analytics.get("data_sufficiency", False)
    baseline_shifts = analytics.get("baseline_shifts", {})
    range_trend = analytics.get("range_trend")
    crisis_flag = analytics.get("crisis_flag", False)
    has_reflection_data = analytics.get("has_reflection_data", False)
    reflection_count = analytics.get("reflection_count", 0)

    if not sufficient:
        return [{
            "type": "insufficient_data",
            "title": "Not Enough Data Yet",
            "message": "Keep journaling to unlock insights. We need at least 3 entries from this week.",
            "confidence": 0.0
        }]

    # Crisis card — always first if flagged
    if crisis_flag:
        insights.append({
            "type": "crisis",
            "title": "You've Been Carrying a Lot",
            "message": "It sounds like you've been carrying a lot lately. You don't have to work through this alone — consider reaching out to someone you trust.",
            "confidence": weekly_confidence
        })

    # Baseline shift
    if baseline_shifts:
        largest_shift = max(baseline_shifts.items(), key=lambda x: x[1]["magnitude"])
        emotion, shift_data = largest_shift
        direction = shift_data["direction"]
        magnitude = shift_data["magnitude"]
        insights.append({
            "type": "baseline_shift",
            "title": f"{emotion.capitalize()} Has {direction.capitalize()}",
            "message": f"Your {emotion.lower()} has {direction} by {magnitude}% compared to your usual baseline.",
            "confidence": weekly_confidence
        })

    # Emotional range trend
    if range_trend and range_trend["trend"] != "stable":
        trend_type = range_trend["trend"]
        if trend_type == "expanding":
            insights.append({
                "type": "range_expanding",
                "title": "Emotional Range Expanding",
                "message": "You're expressing more diverse feelings in your entries lately.",
                "confidence": weekly_confidence
            })
        elif trend_type == "contracting":
            insights.append({
                "type": "range_contracting",
                "title": "Emotional Range Narrowing",
                "message": "Your recent entries show less emotional variety than before.",
                "confidence": weekly_confidence
            })

    # Within-week trends
    if trends and len(insights) < 4:
        for emotion, direction in list(trends.items())[:1]:
            if direction == "increasing":
                insights.append({
                    "type": "trend_increasing",
                    "title": f"{emotion.capitalize()} Building Up",
                    "message": f"Your {emotion.lower()} appears to be increasing over the course of this week.",
                    "confidence": weekly_confidence
                })
            else:
                insights.append({
                    "type": "trend_decreasing",
                    "title": f"{emotion.capitalize()} Declining",
                    "message": f"Your {emotion.lower()} seems to be decreasing as the week progresses.",
                    "confidence": weekly_confidence
                })

    # Reflection depth insight
    if has_reflection_data and len(insights) < 4:
        insights.append({
            "type": "reflection_depth",
            "title": "You Went Deeper",
            "message": f"You reflected on {reflection_count} {'entry' if reflection_count == 1 else 'entries'} this week — exploring beyond what you wrote.",
            "confidence": weekly_confidence
        })

    # High entropy
    if not insights and entropy and entropy >= 2.0:
        insights.append({
            "type": "high_diversity",
            "title": "Wide Emotional Range",
            "message": "You experienced significant emotional variety this week.",
            "confidence": weekly_confidence
        })

    # Fallback
    if not insights:
        dominant = max(distribution, key=distribution.get) if distribution else "neutral"
        insights.append({
            "type": "weekly_summary",
            "title": "This Week's Snapshot",
            "message": f"Your entries this week were most often characterized by {dominant.lower()}.",
            "confidence": weekly_confidence
        })

    return insights
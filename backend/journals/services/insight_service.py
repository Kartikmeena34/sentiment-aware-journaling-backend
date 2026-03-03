def generate_insight(analytics):
    weekly_confidence = analytics.get("weekly_confidence", 0.0)
    distribution = analytics.get("weekly_distribution", {})
    entropy = analytics.get("emotional_entropy")
    trends = analytics.get("trends", {})
    sufficient = analytics.get("data_sufficiency", False)

    if not sufficient:
        return "Keep journaling to see clearer emotional patterns."

    if not distribution:
        return "Your entries this week did not contain enough emotional signal."

    dominant = max(distribution, key=distribution.get)
    dominant_score = distribution[dominant]


    uncertainty_prefix = ""

    if weekly_confidence < 0.5:
        uncertainty_prefix = "Your entries may suggest that "
    elif weekly_confidence < 0.65:
        uncertainty_prefix = "It seems that "

    # -----------------------------
    # Conservative Dominance Framing
    # -----------------------------
    dominance_msg = ""

    if dominant_score > 0.65:
        dominance_msg = (
            f"{uncertainty_prefix}{dominant.capitalize().lower()} was strongly present..."
        )
    elif 0.45 <= dominant_score <= 0.65:
        dominance_msg = (
            f"{uncertainty_prefix}{dominant.capitalize().lower()} showed up more often than other emotions this week."
        )
    elif 0.30 <= dominant_score < 0.45:
        dominance_msg = (
            f"{uncertainty_prefix}{dominant.capitalize().lower()} appeared slightly more frequently this week."
        )
    else:
        # Weak dominance → don't highlight it
        dominance_msg = ""

    # -----------------------------
    # Entropy-Based Range Framing
    # -----------------------------
    range_msg = ""

    if entropy is not None:
        if entropy >= 2.0:
            range_msg = "It looks like you experienced a wide range of emotions this week."
        elif 1.0 <= entropy < 2.0:
            range_msg = "Several emotions appeared throughout your entries this week."
        # For low entropy, dominance message already handles it.

    # -----------------------------
    # Trend Framing
    # -----------------------------
    trend_msgs = []

    for emotion, direction in trends.items():
        if direction == "increasing":
            trend_msgs.append(
                f"{emotion.capitalize()} appears to be increasing."
            )
        elif direction == "decreasing":
            trend_msgs.append(
                f"{emotion.capitalize()} seems to be decreasing."
            )

    trend_msg = " ".join(trend_msgs)

    # -----------------------------
    # Combine Carefully
    # -----------------------------
    parts = [dominance_msg, range_msg, trend_msg]
    final_message = " ".join(part for part in parts if part).strip()

    return final_message
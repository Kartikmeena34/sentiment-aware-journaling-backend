def generate_insight(analytics):
    distribution = analytics["weekly_distribution"]
    stability = analytics["stability_score"]
    trend = analytics["trends"]

    if not distribution:
        return "Keep journaling to build emotional insights."

    dominant = max(distribution, key=distribution.get)

    # Stability-based insight
    if stability > 0.8:
        stability_msg = "Your emotions have been relatively consistent."
    elif stability < 0.3:
        stability_msg = "Your emotions have been fluctuating frequently."
    else:
        stability_msg = "Your emotional pattern shows moderate variation."

    # Trend-based insight
    trend_msgs = []
    for emotion, direction in trend.items():
        if direction == "increasing":
            trend_msgs.append(f"{emotion.capitalize()} appears to be increasing.")
        elif direction == "decreasing":
            trend_msgs.append(f"{emotion.capitalize()} seems to be decreasing.")

    trend_msg = " ".join(trend_msgs)

    return f"This week, {dominant} has been most frequent. {stability_msg} {trend_msg}"
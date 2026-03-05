# insight_service.py

def generate_insight(analytics):
    """
    Generate comparative insights based on analytics data.
    Prioritizes insights that reveal patterns the user couldn't see themselves.
    """
    weekly_confidence = analytics.get("weekly_confidence", 0.0)
    distribution = analytics.get("weekly_distribution", {})
    entropy = analytics.get("emotional_entropy")
    trends = analytics.get("trends", {})
    sufficient = analytics.get("data_sufficiency", False)
    baseline_shifts = analytics.get("baseline_shifts", {})
    range_trend = analytics.get("range_trend")
    
    # Handle insufficient data
    if not sufficient:
        return "Keep journaling to unlock insights. We need at least 3 entries from this week."
    
    if not distribution:
        return "Your entries this week didn't contain clear emotional signals. Try writing more about how you're feeling."
    
    # ============================================================
    # PRIORITY 1: Baseline Shifts (Most Valuable)
    # ============================================================
    if baseline_shifts:
        # Find the largest shift
        largest_shift = max(baseline_shifts.items(), key=lambda x: x[1]["magnitude"])
        emotion, shift_data = largest_shift
        
        direction = shift_data["direction"]
        magnitude = shift_data["magnitude"]
        
        # Add confidence qualifier if predictions are uncertain
        confidence_qualifier = ""
        if weekly_confidence < 0.6:
            confidence_qualifier = "It seems "
        
        baseline_message = (
            f"{confidence_qualifier}Your {emotion.lower()} has {direction} by {magnitude}% "
            f"compared to your usual baseline over the last month."
        )
        
        # Add context if multiple shifts detected
        if len(baseline_shifts) > 1:
            other_shifts = [e for e in baseline_shifts.keys() if e != emotion]
            if other_shifts:
                baseline_message += f" Your {other_shifts[0].lower()} also shifted noticeably."
        
        return baseline_message
    
    # ============================================================
    # PRIORITY 2: Emotional Range Trend
    # ============================================================
    if range_trend and range_trend["trend"] != "stable":
        trend_type = range_trend["trend"]
        
        if trend_type == "expanding":
            return "Your emotional range is expanding — you're expressing more diverse feelings in your entries lately."
        elif trend_type == "contracting":
            return "Your emotional range is narrowing — your recent entries show less emotional variety than before."
    
    # ============================================================
    # PRIORITY 3: Within-Week Trends
    # ============================================================
    if trends:
        # Take the first detected trend
        strongest_trend = list(trends.items())[0]
        emotion, direction = strongest_trend
        
        if direction == "increasing":
            return f"Your {emotion.lower()} appears to be building up over the course of this week."
        else:
            return f"Your {emotion.lower()} seems to be declining as the week progresses."
    
    # ============================================================
    # PRIORITY 4: High Entropy Observation
    # ============================================================
    if entropy and entropy >= 2.0:
        return "You experienced a wide range of emotions this week — your entries reflect significant emotional variety."
    
    # ============================================================
    # FALLBACK: Neutral Acknowledgment
    # ============================================================
    dominant = max(distribution, key=distribution.get)
    dominant_score = distribution[dominant]
    
    # Only mention dominance if it's actually significant
    if dominant_score > 0.5:
        return f"Your entries this week were most often characterized by {dominant.lower()}."
    else:
        return "Your entries this week showed a balanced mix of emotions."


def generate_multiple_insights(analytics):
    """
    Generate up to 3 distinct insights for display in cards.
    Returns a list of insight objects with type and message.
    """
    insights = []
    
    weekly_confidence = analytics.get("weekly_confidence", 0.0)
    distribution = analytics.get("weekly_distribution", {})
    entropy = analytics.get("emotional_entropy")
    trends = analytics.get("trends", {})
    sufficient = analytics.get("data_sufficiency", False)
    baseline_shifts = analytics.get("baseline_shifts", {})
    range_trend = analytics.get("range_trend")
    
    # Handle insufficient data
    if not sufficient:
        return [{
            "type": "insufficient_data",
            "title": "Not Enough Data Yet",
            "message": "Keep journaling to unlock insights. We need at least 3 entries from this week.",
            "confidence": 0.0
        }]
    
    # Insight 1: Baseline Shift
    if baseline_shifts:
        largest_shift = max(baseline_shifts.items(), key=lambda x: x[1]["magnitude"])
        emotion, shift_data = largest_shift
        
        direction = shift_data["direction"]
        magnitude = shift_data["magnitude"]
        
        insights.append({
            "type": "baseline_shift",
            "title": f"{emotion.capitalize()} Has {direction.capitalize()}",
            "message": f"Your {emotion.lower()} has {direction} by {magnitude}% compared to your usual baseline over the last month.",
            "confidence": weekly_confidence
        })
    
    # Insight 2: Emotional Range Trend
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
    
    # Insight 3: Within-Week Trends
    if trends and len(insights) < 3:
        for emotion, direction in list(trends.items())[:1]:  # Take first trend
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
    
    # Insight 4: High Entropy (if no other insights)
    if not insights and entropy and entropy >= 2.0:
        insights.append({
            "type": "high_diversity",
            "title": "Wide Emotional Range",
            "message": "You experienced significant emotional variety this week.",
            "confidence": weekly_confidence
        })
    
    # Fallback: At least return something
    if not insights:
        dominant = max(distribution, key=distribution.get) if distribution else "neutral"
        insights.append({
            "type": "weekly_summary",
            "title": "This Week's Snapshot",
            "message": f"Your entries this week were most often characterized by {dominant.lower()}.",
            "confidence": weekly_confidence
        })
    
    return insights
# app/services/fetch/scoring.py
from datetime import datetime, timezone

# ---------------------------------------------------------
# SOFT RANKING
# ---------------------------------------------------------

CATEGORY_RANKING_BIAS = {
    "sports": 0.10,
    "business": 0.08,
    "technology": 0.08,
    "health": 0.06,
    "science": 0.06,
    "entertainment": 0.05,
    "general": 0.0
}

def compute_ranking_score(confidence, status, published_date, category):
    confidence_part = confidence * 0.5
    analysis_part = 0.25 if status == "completed" else 0.0
    recency_part = 0.0

    if published_date:
        try:
            published = datetime.fromisoformat(published_date.replace("Z", "+00:00"))
            age_hours = (datetime.now(timezone.utc) - published).total_seconds() / 3600
            recency_part = max(0.0, 1.0 - min(age_hours / 48, 1.0)) * 0.15
        except Exception:
            pass

    category_bias = CATEGORY_RANKING_BIAS.get(category, 0.0)
    return round(confidence_part + analysis_part + recency_part + category_bias, 3)

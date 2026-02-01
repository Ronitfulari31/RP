def compute_confidence(results, query_context):
    """
    Computes a confidence score for the search results.
    Takes into account:
    1. Strength of the top match
    2. Separation between top and average scores
    3. Category relevance from LLM
    4. Temporal intent satisfaction
    """
    if not results:
        return {
            "confidence": 0.0,
            "reason": "No relevant articles found"
        }

    # Try to use final_score (reranked) or boosted_score (retrieved)
    scores = [r.get("_final_score", r.get("boosted_score", 0)) for r in results]

    top_score = scores[0]
    avg_score = sum(scores) / len(scores) if scores else 0

    # Signal 1: strength of top match
    # Normalizing a bit since rerank scores can be high/low
    strength = min(max(top_score / 10.0, 0.0), 1.0) if top_score > 1 else min(top_score, 1.0)

    # Signal 2: separation (confidence that top is better than others)
    separation = min(max((top_score - avg_score), 0.0), 1.0) if avg_score else 0

    # Signal 3: category relevance
    category_scores = query_context.get("category_scores", {})
    category_confidence = max(category_scores.values(), default=0.5)

    # Signal 4: temporal intent satisfaction
    time_context = query_context.get("time_window_days")
    time_confidence = 1.0 if time_context else 0.8

    confidence = (
        strength * 0.4 +
        separation * 0.2 +
        category_confidence * 0.2 +
        time_confidence * 0.2
    )

    confidence = round(min(max(confidence, 0.0), 1.0), 2)

    reason = "High relevance match"
    if confidence < 0.4:
        reason = "Results weakly match the query"
    elif confidence < 0.6:
        reason = "Results partially match the query"

    return {
        "confidence": confidence,
        "reason": reason
    }

from datetime import datetime, timezone


class ArticleRanker:
    """
    Computes a deterministic relevance score for articles.
    """

    TIER_WEIGHTS = {
        "city": 100,
        "state": 80,
        "country": 60,
        "continent": 40,
        "global": 20
    }

    def score(self, article: dict, context: dict, tier_level: str) -> int:
        score = 0

        # ---------------- Tier priority ----------------
        score += self.TIER_WEIGHTS.get(tier_level, 0)

        # ---------------- Location match ----------------
        if context.get("city") and article.get("city") == context["city"]:
            score += 30
        elif context.get("state") and article.get("state") == context["state"]:
            score += 20
        elif context.get("country") and article.get("country") == context["country"]:
            score += 10

        # ---------------- Language match ----------------
        if article.get("language") in context.get("language", []):
            score += 15
        else:
            score += 5  # fallback language

        # ---------------- Category match ----------------
        if context.get("category") != "unknown":
            if article.get("category") == context["category"]:
                score += 15

        # ---------------- Recency boost ----------------
        published_at = article.get("published_date") or article.get("created_at")
        if published_at:
            # Ensure published_at is timezone-aware for comparison if it's naive
            if isinstance(published_at, datetime):
                if published_at.tzinfo is None:
                    # Assume naive datetimes from DB are UTC
                    published_at = published_at.replace(tzinfo=timezone.utc)
                
                now = datetime.now(timezone.utc)
                diff = now - published_at
                hours_old = diff.total_seconds() / 3600
                score += max(0, 20 - int(hours_old))

        return score

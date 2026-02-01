# Source Selector
"""
Source Selector
----------------
Selects RSS sources based on resolved request context.

Features:
- Country match with global wildcard support
- Soft category matching (world <-> national)
- Ordered fallback:
    1. Exact country match
    2. Continent-level match
    3. Global sources
"""

from app.services.discovery.fetch.rss_sources import RSS_SOURCES


def _language_match(context_languages, source_languages):
    return any(lang in source_languages for lang in context_languages)


def _category_match(requested_category, source_categories):
    """
    Soft category matching:
    - Exact match
    - world <-> national fallback
    """
    if requested_category == "unknown":
        return True

    if requested_category in source_categories:
        return True

    # Soft fallback
    if requested_category == "national" and "world" in source_categories:
        return True

    if requested_category == "world" and "national" in source_categories:
        return True

    return False


def _filter_sources(context, sources):
    """
    Apply language + category filtering.
    Country/continent handled separately for fallback logic.
    """
    filtered = []

    for source in sources:
        # Language check
        if not _language_match(context["language"], source["language"]):
            continue

        # Category check (soft)
        if not _category_match(context["category"], source["category"]):
            continue

        filtered.append(source)

    return filtered


def select_sources(context: dict):
    """
    Select RSS sources based on resolver context.

    Fallback order:
    1. Exact country match
    2. Continent match
    3. Global sources
    """

    # -------------------------------
    # 1. Exact country match
    # -------------------------------
    country_sources = [
        s for s in RSS_SOURCES
        if s["country"] == context["country"]
    ]

    country_sources = _filter_sources(context, country_sources)
    if country_sources:
        return country_sources

    # -------------------------------
    # 2. Continent-level fallback
    # -------------------------------
    continent_sources = [
        s for s in RSS_SOURCES
        if s["continent"] == context["continent"]
    ]

    continent_sources = _filter_sources(context, continent_sources)
    if continent_sources:
        return continent_sources

    # -------------------------------
    # 3. Global fallback
    # -------------------------------
    global_sources = [
        s for s in RSS_SOURCES
        if s["country"] == "global"
    ]

    global_sources = _filter_sources(context, global_sources)
    if global_sources:
        return global_sources

    # -------------------------------
    # 4. Nothing matched
    # -------------------------------
    return []

from app.services.intelli_search.ollama_client import get_ollama_llm
import json

# Lazy initialization to avoid blocking server startup
_llm = None

def _get_llm():
    global _llm
    if _llm is None:
        _llm = get_ollama_llm(temperature=0.1)
    return _llm

SYSTEM_PROMPT = """
You are an advanced news query intelligence system. Your goal is to DEEPLY UNDERSTAND what the user truly wants to find.

## Your Core Mission:
Analyze the user's query to understand:
1. **Primary Intent**: What is the user really looking for? (breaking news, background info, analysis, updates, etc.)
2. **Topic Focus**: What subject matter are they interested in?
3. **Scope & Context**: Are they looking for local, national, or global coverage?
4. **Implicit Needs**: What might they want to know that they didn't explicitly ask?

## Available News Categories (MUST use these exact values):
- **disaster**: Natural disasters, earthquakes, floods, hurricanes, tsunamis, wildfires, droughts, avalanches
- **terror**: Terrorism, terrorist attacks, bombings, security threats, extremism, violence
- **infrastructure**: Construction, buildings, roads, bridges, transportation, urban development, public works
- **business**: Economy, markets, trade, finance, companies, stocks, investments, corporate news
- **politics**: Elections, government, parliament, policy, legislation, political parties, diplomacy
- **technology**: Tech innovations, AI, software, digital transformation, startups, science breakthroughs

## Analysis Framework:

**Step 1 - Understand the Core Intent:**
- If user asks about "all disaster news" → They want to see ALL disaster-related articles
- If user asks about "all terror news" → They want to see ALL terrorism-related articles 
- If user asks about "all infrastructure news" → They want to see ALL infrastructure-related articles
- If user asks about "all business news" → They want to see ALL business-related articles
- If user asks about "all politics news" → They want to see ALL politics-related articles
- If user asks about "all technology news" → They want to see ALL technology-related articles
- If user asks about "China infrastructure" → They want infrastructure news specifically from China
- If user asks about "recent terror attacks" → They want recent terrorism news with time sensitivity

**Step 2 - Extract Key Information:**
- **Entities**: People (politicians, CEOs), Places (countries, cities), Organizations (companies, agencies)
- **Categories**: Map the topic to ONE OR MORE relevant categories from the list above
- **Geographic Scope**: Is this about a specific country/region or global?
- **Time Sensitivity**: Does "recent", "latest", "today" indicate they want very fresh news?

**Step 3 - Expand Search Terms:**
- Think of synonyms and related terms that would help find relevant articles
- Example: "disaster" → ["disaster", "catastrophe", "emergency", "crisis"]
- Keep it focused - max 5-6 terms

## Critical Rules:
1. **Category Precision**: ONLY use categories from the list above. Match the PRIMARY topic.
2. **Entity Accuracy**: Only extract entities that are explicitly mentioned or strongly implied
3. **No Hallucination**: Don't add information that isn't in the query
4. **User-Centric**: Think about what results would BEST serve the user's need

## Response Format (JSON ONLY):
{
  "intent": "news",
  "entities": {
    "people": ["Person Name"],
    "locations": ["Country", "City"],
    "organizations": ["Company", "Agency"]
  },
  "expanded_terms": ["term1", "synonym2", "related3"],
  "suggested_filters": {
    "country": ["CountryName"],
    "category": ["disaster", "terror"]
  }
}

**IMPORTANT**: 
- Return ONLY valid JSON, no explanations
- Categories MUST be from the list above
- If unsure about a category, choose the closest match
- Multiple categories are OK if the query spans topics
- Empty arrays are OK if no entities/filters apply
"""

import re

def infer_time_window_days(query: str):
    query = query.lower()

    if re.search(r"\b(today|latest|current|now)\b", query):
        return 1
    if re.search(r"\b(yesterday)\b", query):
        return 2
    if re.search(r"\b(recent|recently)\b", query):
        return 7
    if re.search(r"\b(last week)\b", query):
        return 7
    if re.search(r"\b(last month)\b", query):
        return 30

    return None

def normalize_expanded_terms(expanded_terms, max_terms=6):
    """Limit and clean expanded terms to avoid noise."""
    if not expanded_terms: return []
    if not isinstance(expanded_terms, list): expanded_terms = [expanded_terms]
    cleaned = []
    for term in expanded_terms:
        if isinstance(term, str) and len(term.strip()) > 2:
            cleaned.append(term.strip())
    return list(dict.fromkeys(cleaned))[:max_terms]

def normalize_signals(data: dict, key: str) -> dict:
    """
    Ensures 'entities' or 'suggested_filters' is a flat dictionary.
    Handles cases where LLM returns a list of objects like [{"type": "country", "value": "China"}]
    """
    raw = data.get(key, {})
    if isinstance(raw, dict):
        # Already a dict, but check if values are strings/lists
        return {k: v if isinstance(v, (list, str)) else str(v) for k, v in raw.items()}
    
    if isinstance(raw, list):
        # Convert list of {type/key, value} to dict
        normalized = {}
        for item in raw:
            if isinstance(item, dict):
                # Try to find a key/value pair
                k = item.get("type") or item.get("key") or next(iter(item.keys()), None)
                v = item.get("value") or item.get("name") or next(iter(item.values()), None)
                if k and v:
                    if k not in normalized: normalized[k] = []
                    if isinstance(v, list): normalized[k].extend(v)
                    else: normalized[k].append(v)
        return normalized
    
    return {}

from app.services.intelli_search.query_translator import translate_query_if_needed

def process_query(query: str) -> dict:
    """
    Converts a human language query into structured search signals.
    """
    # STEP 4 — Translate query first
    translation = translate_query_if_needed(query)
    canonical_query = translation["translated_query"]
    
    # 🎯 DIRECT CATEGORY MAPPING: Handle obvious category keywords before LLM
    # This ensures "disaster news" maps to "disaster" category, not "accidents"
    query_lower = canonical_query.lower()
    direct_categories = []
    
    CATEGORY_KEYWORDS = {
        "disaster": ["disaster", "earthquake", "flood", "tsunami", "hurricane", "tornado"],
        "terror": ["terror", "terrorism", "attack", "bombing"],
        "infrastructure": ["infrastructure", "construction", "building", "bridge", "road"],
        "business": ["business", "economy", "market", "trade", "finance"],
        "politics": ["politics", "election", "government", "parliament"],
        "technology": ["technology", "tech", "ai", "software", "innovation"]
    }
    
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in query_lower for keyword in keywords):
            direct_categories.append(category)
    
    # Use canonical (English) query for LLM
    prompt = f'User Query: "{canonical_query}"'

    response = _get_llm().invoke(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
    )

    raw_content = response.content.strip() if hasattr(response, 'content') else str(response).strip()
    
    # Robust JSON extraction
    if "{" in raw_content and "}" in raw_content:
        try:
            start_idx = raw_content.find("{")
            end_idx = raw_content.rfind("}") + 1
            json_str = raw_content[start_idx:end_idx]
            data = json.loads(json_str)
        except Exception as e:
            logger.error(f"Failed to extract JSON in query_processor: {e}")
            data = {}
    else:
        try:
            data = json.loads(raw_content)
        except:
            data = {}

    if isinstance(data, list) and len(data) > 0:
        data = data[0]
    if not isinstance(data, dict):
        data = {}

    # Standardize all signals
    entities = normalize_signals(data, "entities")
    suggested_filters = normalize_signals(data, "suggested_filters")
    
    # Fallback to CANONICAL query for expansion if needed
    expanded_terms = normalize_expanded_terms(data.get("expanded_terms", [canonical_query]))
    
    # Detect time window from CANONICAL query (English regex)
    time_window_days = infer_time_window_days(canonical_query)
    
    # STEP 5 — Detect multi-intent queries (NEW - Phase 10)
    from app.services.intelli_search.query_decomposer import detect_query_decomposition
    decomposition = detect_query_decomposition(canonical_query)
    
    # 🎯 Merge direct categories with LLM suggestions (direct takes priority)
    llm_categories = suggested_filters.get("category", [])
    if direct_categories:
        # Use direct keyword matches, they're more reliable
        final_categories = direct_categories
    elif llm_categories:
        # Fall back to LLM if no direct match
        final_categories = llm_categories if isinstance(llm_categories, list) else [llm_categories]
    else:
        final_categories = []
    
    # Update suggested_filters with final categories
    if final_categories:
        suggested_filters["category"] = final_categories

    return {
        "original_query": query,
        "canonical_query": canonical_query,
        "detected_language": translation["detected_language"],
        "intent": data.get("intent", "news"),
        "entities": entities,
        "expanded_terms": expanded_terms,
        "suggested_filters": suggested_filters,
        "time_window_days": time_window_days,
        "decomposition": decomposition  # NEW
    }

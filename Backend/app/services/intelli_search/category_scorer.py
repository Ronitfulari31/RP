import json
from app.services.intelli_search.ollama_client import get_ollama_llm

llm = get_ollama_llm()

CATEGORY_PROMPT = """
You are ranking news relevance.

Query:
"{query}"

Below is a list of possible news categories.
Return a JSON object mapping each category to a relevance score between 0 and 1.

Rules:
- Higher score = more relevant to the query
- Irrelevant categories should be near 0
- Do NOT invent categories
- Only return valid JSON

Categories:
{categories}
"""

def score_categories_with_llm(query: str, categories: list[str]) -> dict:
    if not categories:
        return {}

    messages = [
        {"role": "system", "content": "You are a news relevance ranking engine. Return ONLY JSON."},
        {"role": "user", "content": CATEGORY_PROMPT.format(
            query=query,
            categories=", ".join(sorted(set(categories)))
        )}
    ]

    try:
        response = llm.invoke(messages)
        parsed = json.loads(response.content)

        return {
            k.lower(): float(v)
            for k, v in parsed.items()
            if isinstance(v, (int, float))
        }

    except Exception as e:
        print(f"DEBUG: Category Scorer Failed: {e}")
        # Fail safe: neutral scores
        return {c.lower(): 1.0 for c in categories}

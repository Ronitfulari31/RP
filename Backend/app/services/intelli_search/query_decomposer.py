from app.services.intelli_search.ollama_client import get_ollama_llm
import json
import logging

logger = logging.getLogger(__name__)

DECOMPOSE_PROMPT = """You are a query intent analyzer for a news search engine.

Task:
Determine whether the user query contains multiple distinct intents
(e.g., comparisons, multiple topics, or multiple regions).

Rules:
- Do NOT retrieve news
- Do NOT add new concepts
- Only split if truly necessary
- Keep sub-queries simple and factual

Respond ONLY in valid JSON.

Schema:
{{
  "is_multi_intent": boolean,
  "reason": string,
  "sub_queries": array of strings
}}

User query:
"{query}"
"""

def detect_query_decomposition(query: str) -> dict:
    """
    Detect if a query contains multiple distinct intents.
    
    Examples:
    - "road safety in china vs india" -> Multi-intent (comparison)
    - "roads in china" -> Single intent
    - "terrorist attacks in paris and london" -> Multi-intent (multiple locations)
    
    Returns:
        dict: {
            "is_multi_intent": bool,
            "reason": str,
            "sub_queries": list[str]
        }
    """
    
    try:
        llm = get_ollama_llm(temperature=0.0)  # Deterministic for consistency
        
        response = llm.invoke([{
            "role": "user",
            "content": DECOMPOSE_PROMPT.format(query=query)
        }])
        
        raw_content = response.content.strip() if hasattr(response, 'content') else str(response).strip()
        
        # Robust JSON extraction (handles markdown ticks or leading/trailing text)
        if "{" in raw_content and "}" in raw_content:
            try:
                # Find the first { and last }
                start_idx = raw_content.find("{")
                end_idx = raw_content.rfind("}") + 1
                json_str = raw_content[start_idx:end_idx]
                parsed = json.loads(json_str)
            except Exception as e:
                logger.error(f"Failed to extract JSON from content: {e}")
                parsed = {}
        else:
            try:
                parsed = json.loads(raw_content)
            except:
                parsed = {}
        
        # Safety guardrails
        if not parsed.get("is_multi_intent"):
            return {
                "is_multi_intent": False,
                "reason": parsed.get("reason", "Single intent"),
                "sub_queries": []
            }
        
        sub_queries = parsed.get("sub_queries", [])
        
        # Validate sub-queries
        if not isinstance(sub_queries, list) or len(sub_queries) < 2:
            logger.warning(f"Invalid decomposition for '{query}': {sub_queries}")
            return {
                "is_multi_intent": False,
                "reason": "Invalid decomposition",
                "sub_queries": []
            }
        
        logger.info(f"Multi-intent detected: {query} -> {sub_queries}")
        
        return {
            "is_multi_intent": True,
            "reason": parsed.get("reason", "Multiple intents detected"),
            "sub_queries": sub_queries
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing failed for query '{query}': {e}")
        # Hard fallback: never break pipeline
        return {
            "is_multi_intent": False,
            "reason": "LLM parsing failed",
            "sub_queries": []
        }
    except Exception as e:
        logger.error(f"Query decomposition failed for '{query}': {e}")
        # Hard fallback: never break pipeline
        return {
            "is_multi_intent": False,
            "reason": f"Error: {str(e)}",
            "sub_queries": []
        }

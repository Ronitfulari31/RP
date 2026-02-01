from app.services.intelli_search.ollama_client import get_ollama_llm

# Lazy initialization
_validator_llm = None

def _get_validator_llm():
    global _validator_llm
    if _validator_llm is None:
        _validator_llm = get_ollama_llm(temperature=0.0)  # Zero temperature for binary decisions
    return _validator_llm


def is_article_about_query(query: str, article_text: str) -> bool:
    """
    Returns True if article is primarily about the query topic.
    False otherwise.
    
    This is an entailment check, not similarity scoring.
    Uses binary YES/NO output to avoid hallucination.
    """
    
    if not article_text or not query:
        return False
    
    llm = _get_validator_llm()
    
    prompt = f"""Answer ONLY with YES or NO.

Question:
Does the following news article contain significant information about, or is it directly relevant to, the topic described in the query?
(If the article covers multiple topics including the query topic, answer YES.)

Query:
"{query}"

Article:
"{article_text[:1200]}"

Answer (YES or NO):"""

    try:
        response = llm.invoke([{"role": "user", "content": prompt}])
        answer = response.content.strip().upper()
        
        # Accept YES, Y, or variations
        return answer in ["YES", "Y", "TRUE", "1"]
    except Exception as e:
        print(f"Is-about validator error: {e}")
        return True  # Fail open to avoid breaking search

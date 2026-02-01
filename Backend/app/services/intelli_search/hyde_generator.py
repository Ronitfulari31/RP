def generate_hypothetical_answer(query, llm):
    """
    Generates a short, factual, news-style pseudo-answer
    used ONLY for vector retrieval (never shown to user).
    """

    prompt = f"""
    Write a factual, neutral news-style answer (maximum 3 sentences)
    that would directly answer the query below.
    
    Do NOT speculate.
    Do NOT give opinions.
    Do NOT mention uncertainty.
    
    Query:
    {query}
    """

    response = llm.invoke(prompt)

    # Safety guard
    text = response.content.strip()
    sentences = text.split(".")[:3]

    return ". ".join(sentences).strip()

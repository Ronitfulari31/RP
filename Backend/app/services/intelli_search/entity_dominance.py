def entity_dominance_score(entity: str, text: str) -> float:
    """
    Measures how dominant an entity is in the text.
    
    Returns a ratio of entity mentions to total tokens.
    Higher score = entity is more central to the article.
    
    Args:
        entity: The entity to check (e.g., "china", "roads")
        text: The article text
        
    Returns:
        Float between 0.0 and 1.0 representing dominance
    """
    
    if not text or not entity:
        return 0.0
    
    entity = entity.lower()
    text = text.lower()
    
    total_tokens = len(text.split())
    entity_mentions = text.count(entity)
    
    if total_tokens == 0:
        return 0.0
    
    # Calculate dominance ratio
    dominance = entity_mentions / total_tokens
    
    return min(dominance, 1.0)  # Cap at 1.0


def multi_entity_dominance(entities: list, text: str) -> float:
    """
    Calculate combined dominance for multiple entities.
    Useful for queries like "roads in china" (both "roads" and "china").
    
    Returns the average dominance across all entities.
    """
    
    if not entities or not text:
        return 0.0
    
    scores = [entity_dominance_score(entity, text) for entity in entities]
    
    return sum(scores) / len(scores) if scores else 0.0

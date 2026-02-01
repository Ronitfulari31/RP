def explain_result(doc, query_context):
    """
    Generates a list of reasons why an article was ranked for a given query.
    Grounded in the signals derived during retrieval and scoring.
    """
    explanations = []

    # 1. Category relevance
    category_scores = query_context.get("category_scores", {})
    category = (doc.get("category") or doc.get("inferred_category") or "").lower()
    if category and category_scores.get(category, 0) > 0.6:
        explanations.append(f"Matches your topic interest ({category.title()})")

    # 2. Entity match
    entities = query_context.get("entities", {})
    people = entities.get("people", [])
    if isinstance(people, str): people = [people]
    
    text_to_search = (doc.get("title", "") + " " + doc.get("summary", "")).lower()
    for person in people:
        if str(person).lower() in text_to_search:
            explanations.append(f"Mentions {person}")
            break

    # 3. Location relevance
    suggested_filters = query_context.get("suggested_filters", {})
    countries = suggested_filters.get("country", [])
    if isinstance(countries, str): countries = [countries]
    
    doc_country = doc.get("country", "").lower()
    if doc_country and any(c.lower() == doc_country for c in countries):
        explanations.append(f"Relevant to {doc.get('country')}")

    # 4. Time relevance
    # Using time_window_days as a proxy for 'published recently' intent
    if query_context.get("time_window_days"):
        explanations.append("Matches your requested time frame")

    # 5. Retrieval Channel Match
    if doc.get("lexical_match"):
        explanations.append("Direct keyword match")

    if doc.get("semantic_match"):
        explanations.append("Semantically related to your query")
        explanations.append("HyDE factual alignment")

    # 6. Cross-Encoder Accuracy
    if doc.get("bge_score") and doc.get("bge_score") > -2.0:
        explanations.append("High cross-encoder relevance score")
    
    # 7. Semantic Gate Validations (NEW)
    category_confidence = doc.get("category_confidence", 0)
    if category_confidence >= 0.7:
        explanations.append("High category classification confidence")
    elif category_confidence >= 0.5:
        explanations.append("Moderate category confidence")
    
    # Entity dominance (if available)
    if doc.get("_entity_dominance_score"):
        if doc["_entity_dominance_score"] > 0.02:
            explanations.append("Topic is central to the article")
    
    # Is-about validation (if passed)
    if doc.get("_is_about_validated"):
        explanations.append("Verified as primarily about your query")

    return explanations

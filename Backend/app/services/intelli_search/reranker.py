from app.services.intelli_search.bge_reranker import rerank_with_bge
from app.services.intelli_search.is_about_validator import is_article_about_query
from app.services.intelli_search.entity_dominance import entity_dominance_score
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Lazy loading - only initialize when first needed
_ranker = None

def _get_ranker():
    """Lazy load FlashRank to avoid blocking server startup"""
    global _ranker
    if _ranker is None:
        from flashrank import Ranker
        logger.info("Loading FlashRank model (first search)...")
        _ranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2")
        logger.info("FlashRank model loaded successfully")
    return _ranker

# Semantic gate thresholds
MIN_CATEGORY_CONFIDENCE = 0.3  # ENABLED: Now that category_confidence is fixed in pipeline
MIN_ENTITY_DOMINANCE = 0.005   # Penalize if entity appears <0.5% of the time
APPLY_IS_ABOUT_TO_TOP_N = 15   # Increased: Check deeper for relevance if top matches are noisy

def calculate_recency_boost(published_date):
    """
    Calculate recency boost multiplier based on article age.
    Recent articles get higher scores for time-sensitive queries.
    """
    if not published_date:
        return 1.0  # No boost/penalty if date unknown
    
    try:
        if isinstance(published_date, str):
            published_date = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
        
        days_old = (datetime.utcnow() - published_date).days
        
        if days_old <= 1:
            return 1.2  # 20% boost for today's news
        elif days_old <= 7:
            return 1.1  # 10% boost for this week
        elif days_old <= 30:
            return 1.0  # No boost for this month
        else:
            return 0.9  # 10% penalty for old news
    except Exception:
        return 1.0  # Default to no boost on error

def is_broad_category_query(query: str, q_signals: dict = None) -> bool:
    """
    Detect if user is asking for ALL articles in a category.
    Examples: "all disaster news", "show me all terror news", "give me disaster articles"
    
    If true, we should bypass strict semantic gates and return all category matches.
    """
    query_lower = query.lower()
    
    # Check for "all" keyword with category
    broad_indicators = ["all", "show me all", "give me all", "list all", "get all"]
    has_all_keyword = any(indicator in query_lower for indicator in broad_indicators)
    
    # Check if query signals suggest a category filter
    has_category_filter = False
    if q_signals and q_signals.get("suggested_filters", {}).get("category"):
        has_category_filter = True
    
    # If user says "all [category]", bypass gates
    if has_all_keyword and has_category_filter:
        logger.info(f"🎯 Broad category query detected: '{query}' - Bypassing strict semantic gates")
        return True
    
    return False

def rerank(query: str, documents: list, top_k: int = 5, q_signals: dict = None) -> list:
    """
    Multi-stage re-ranking with semantic gates:
    1. FlashRank (Fast) for initial filtering
    2. BGE Cross-Encoder (Deep) for precision
    3. Category Confidence Gate (Quality control)
    4. Entity Dominance Penalty (Topic centrality)
    5. Is-About Validator (Entailment check for top results)
    
    SPECIAL CASE: If user asks for "all [category] news", bypass gates and return all matches.
    """

    if not documents:
        return []

    # print(f"DEBUG: documents[0] type: {type(documents[0])}")

    passages = []
    valid_documents = []
    for i, doc in enumerate(documents):
        if not isinstance(doc, dict):
            print(f"WARNING: Skipping non-dict document: {type(doc)} | Content: {str(doc)[:100]}")
            continue
            
        def _get_text_safe(val):
            if isinstance(val, dict):
                return str(val.get("value") or val.get("en") or list(val.values())[0] if val else "")
            return str(val) if val else ""

        text = " ".join(filter(None, [
            _get_text_safe(doc.get("translated_title")),
            _get_text_safe(doc.get("summary")),
            _get_text_safe(doc.get("translated_summary")),
            _get_text_safe(doc.get("cleaned_text"))
        ]))
        passages.append({
            "id": len(valid_documents),
            "text": text[:1000]
        })
        valid_documents.append(doc)

    from flashrank import RerankRequest
    
    request = RerankRequest(
        query=query,
        passages=passages
    )

    ranker = _get_ranker()  # Lazy load
    results = ranker.rerank(request)

    # Attach FlashRank scores and category boosts
    flashrank_docs = []
    for r in results:
        doc = valid_documents[r["id"]]
        
        # FlashRank score (usually -10 to 10) + LLM Category Boost (0.0 to 1.0)
        semantic_score = r.get("score", 0.0)
        category_boost = doc.get("_category_boost", 0.0)
        
        doc["_flash_score"] = semantic_score
        doc["_final_score"] = semantic_score + category_boost # Used for sorting/pruning
        doc["_debug_score"] = f"Flash: {semantic_score:.4f} | Boost: {category_boost:.2f}"
        
        flashrank_docs.append(doc)

    # if flashrank_docs:
    #    print(f"DEBUG: First FlashRank score: {flashrank_docs[0].get('_flash_score')}")

    # Sort and take top 15 for deep reranking
    flashrank_docs.sort(key=lambda x: x["_final_score"], reverse=True)
    bge_candidates_raw = flashrank_docs[:15]
    
    # print(f"DEBUG: bge_candidates_raw type: {type(bge_candidates_raw)}")
    # if bge_candidates_raw:
    #     print(f"DEBUG: bge_candidates_raw[0] type: {type(bge_candidates_raw[0])}")

    # --- Stage 2: BGE Cross-Encoder ---
    bge_candidates = []
    for doc in bge_candidates_raw:
        try:
            # Define safe extraction helper again or move to outer scope if needed, 
            # but for minimizing diffs, I'll inline the logic or re-use if possible. 
            # Ideally, I should have defined it outside. Let's do simple dict check here.
            
            def _get_text_s(val):
                if isinstance(val, dict):
                    return str(val.get("value") or val.get("en") or list(val.values())[0] if val else "")
                return str(val) if val else ""

            title = _get_text_s(doc.get("translated_title"))
            summary = _get_text_s(doc.get("translated_summary")) or _get_text_s(doc.get("summary"))
            bge_candidates.append({
                "text": f"{title} {summary}",
                "metadata": doc
            })
        except Exception as e:
            print(f"ERROR Stage 2: doc={type(doc)}, err={e}")

    bge_results = rerank_with_bge(
        query=query,
        documents=bge_candidates,
        top_k=top_k * 2  # Get more candidates for filtering
    )

    # --- Stage 3: SEMANTIC GATES (NEW) ---
    
    # Helper to safely get article title
    def safe_title(result):
        title = result.get('translated_title') or result.get('title') or 'Untitled'
        return str(title)[:60]
    
    # Gate 1: Category Confidence Enforcement
    filtered_results = []
    for result in bge_results:
        category_confidence = result.get("category_confidence", 0.0)
        article_category = result.get("category", "")
        
        # Determine if we should be lenient (e.g. if category matches query intent)
        # If the search specifically filtered for this category, we trust it even if confidence is 0.0
        # (Confidence 0.0 often means it's not a disaster, but it can still be a valid news category)
        is_trusted_category = False
        if article_category and article_category != "unknown":
            is_trusted_category = True
            
        # Strict rejection ONLY if confidence is low AND it's not a trusted category
        if category_confidence < MIN_CATEGORY_CONFIDENCE:
            if not is_trusted_category:
                print(f"GATE 1 REJECT: Low category confidence ({category_confidence:.2f}) for: {safe_title(result)}")
                continue
            else:
                # Keep it but apply a small penalty if confidence is 0.0
                if category_confidence == 0.0:
                    result["bge_score"] = result.get("bge_score", 0) * 0.8
                    print(f"GATE 1 CAUTION: Zero confidence but trusted category '{article_category}' for: {safe_title(result)}")
        
        # Penalty for moderate confidence
        elif category_confidence < 0.5:
            result["bge_score"] = result.get("bge_score", 0) * 0.9
        
        filtered_results.append(result)
    
    # Gate 2: Entity Dominance Penalty
    # Extract key entities from query or processed signals
    query_lower = query.lower()
    key_entities = []
    
    # 1. Use high-accuracy entities from LLM/NER if available
    if q_signals:
        entities_data = q_signals.get("entities", {})
        # Flatten locations and organizations into a list
        key_entities.extend([e.lower() for e in entities_data.get("locations", [])])
        key_entities.extend([e.lower() for e in entities_data.get("organizations", [])])
    
    # 2. Add fallback entities and common patterns
    if "china" in query_lower and "china" not in key_entities:
        key_entities.append("china")
    if "india" in query_lower and "india" not in key_entities:
        key_entities.append("india")
    if ("road" in query_lower or "highway" in query_lower or "infrastructure" in query_lower) and "road" not in key_entities:
        key_entities.append("road")
    if ("disaster" in query_lower or "earthquake" in query_lower) and "disaster" not in key_entities:
        key_entities.append("disaster")
    if ("terror" in query_lower or "attack" in query_lower) and "attack" not in key_entities:
        key_entities.append("attack")
    
    for result in filtered_results:
        # Safely build article text with all available fields (FIX: Added title and cleaned_text)
        # Helper for safe text extraction
        def _get_text_s(val):
            if isinstance(val, dict):
                return str(val.get("value") or val.get("en") or list(val.values())[0] if val else "")
            return str(val) if val else ""

        # Safely build article text with all available fields (FIX: Added title and cleaned_text)
        article_text = " ".join(filter(None, [
            _get_text_s(result.get("title")),  # Original title fallback
            _get_text_s(result.get("translated_title")),
            _get_text_s(result.get("summary")),
            _get_text_s(result.get("translated_summary")),
            _get_text_s(result.get("cleaned_text"))[:500] # Use snippet of full text
        ]))
        
        # Calculate entity dominance
        if key_entities:
            dominance_scores = [entity_dominance_score(entity, article_text) for entity in key_entities]
            avg_dominance = sum(dominance_scores) / len(dominance_scores) if dominance_scores else 0
            
            # Penalize if entity is barely mentioned
            if avg_dominance < MIN_ENTITY_DOMINANCE:
                result["bge_score"] = result.get("bge_score", 0) * 0.5
                print(f"GATE 2 PENALTY: Low entity dominance ({avg_dominance:.4f}) for: {safe_title(result)}")
    
    # Re-sort after penalties
    filtered_results.sort(key=lambda x: x.get("bge_score", 0), reverse=True)
    
    # OPTIMIZATION: Apply recency boost to prioritize recent articles
    for result in filtered_results:
        published_date = result.get("published_date")
        recency_multiplier = calculate_recency_boost(published_date)
        
        # Apply boost to final score
        original_score = result.get("bge_score", 0)
        result["bge_score"] = original_score * recency_multiplier
        
        if recency_multiplier != 1.0:
            print(f"RECENCY BOOST: {recency_multiplier:.2f}x for: {safe_title(result)}")
    
    # Re-sort after recency boost
    filtered_results.sort(key=lambda x: x.get("bge_score", 0), reverse=True)
    
    # Gate 3: Is-About Validator (Apply only to SPECIFIC queries, not generic ones)
    # Skip Gate 3 for generic queries like "sports news", "football", "technology"
    def is_specific_query(q):
        """
        Determine if query is specific enough to warrant is-about validation.
        Generic queries: "sports", "news", "football" -> Skip Gate 3
        Specific queries: "roads in china", "terrorist attacks in paris" -> Apply Gate 3
        """
        q_lower = q.lower()
        
        # Generic single-word queries
        generic_terms = ["sports", "news", "football", "basketball", "technology", 
                        "business", "politics", "entertainment", "science"]
        if q_lower in generic_terms:
            return False
        
        # Generic two-word queries
        generic_phrases = ["sports news", "football news", "tech news", "business news"]
        if q_lower in generic_phrases:
            return False
        
        # If query has specific entities or multiple words with context, it's specific
        words = q_lower.split()
        if len(words) >= 3:  # "roads in china" = 3 words
            return True
        
        # If query has location/entity keywords, it's specific
        specific_keywords = ["in", "at", "from", "about", "attack", "disaster", 
                            "road", "highway", "infrastructure", "china", "india"]
        if any(keyword in q_lower for keyword in specific_keywords):
            return True
        
        return False
    
    final_results = []
    
    # 🎯 BYPASS GATES for broad category queries (e.g., "all disaster news")
    if is_broad_category_query(query, q_signals):
        print(f"🎯 BROAD CATEGORY QUERY: Bypassing GATE 3 - returning all category matches")
        return filtered_results[:top_k]
    
    # Only apply Gate 3 if query is specific
    if is_specific_query(query):
        print(f"GATE 3 ACTIVE: Query is specific, applying is-about validation")
        for i, result in enumerate(filtered_results[:APPLY_IS_ABOUT_TO_TOP_N]):
            # Helper for safe text extraction
            def _get_text_s(val):
                if isinstance(val, dict):
                    return str(val.get("value") or val.get("en") or list(val.values())[0] if val else "")
                return str(val) if val else ""

            # Use same robust text builder
            article_text = " ".join(filter(None, [
                _get_text_s(result.get("title")),
                _get_text_s(result.get("translated_title")),
                _get_text_s(result.get("summary")),
                _get_text_s(result.get("translated_summary")),
                _get_text_s(result.get("cleaned_text"))[:800] # Slightly larger snippet for LLM
            ]))
            
            # Binary entailment check
            if is_article_about_query(query, article_text):
                final_results.append(result)
                print(f"GATE 3 PASS: Is-about validated for: {safe_title(result)}")
            else:
                print(f"GATE 3 REJECT: Not primarily about query: {safe_title(result)}")
        
        # Add remaining results without is-about check (already filtered by gates 1 & 2)
        final_results.extend(filtered_results[APPLY_IS_ABOUT_TO_TOP_N:top_k])
    else:
        print(f"GATE 3 SKIPPED: Query is generic, returning all filtered results")
        final_results = filtered_results[:top_k]
    
    return final_results[:top_k]

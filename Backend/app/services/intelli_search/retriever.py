from flask import current_app
import re
from datetime import datetime, timedelta

def _regex_any(terms):
    """Create a safe OR-regex for multiple terms"""
    if not isinstance(terms, list):
        terms = [terms]
    # Filter out empty or non-string terms
    clean_terms = [re.escape(str(t)) for t in terms if t]
    if not clean_terms:
        return None
    return {"$regex": "|".join(clean_terms), "$options": "i"}

# Search Version: v1.0-search (HyDE + Atlas Vector + FlashRank + BGE Rerank)
from app.services.intelli_search.category_scorer import score_categories_with_llm
from app.services.intelli_search.vector_retriever import vector_search
from app.services.intelli_search.ollama_client import get_ollama_llm
from app.services.intelli_search.hyde_generator import generate_hypothetical_answer

def apply_dynamic_category_boost(candidates, query_context):
    if not candidates: return []
    query = query_context.get("canonical_query") or query_context["original_query"]

    # Collect unique categories
    categories = set()
    # Helper to extract string from potential dict
    def extract_cat_str(val):
        if isinstance(val, dict):
            return str(val.get("category") or val.get("value") or "").lower()
        return str(val or "").lower()

    for doc in candidates:
        cat_val = doc.get("category") or doc.get("inferred_category")
        if cat_val:
            categories.add(extract_cat_str(cat_val))

    # Get scores from LLM (0 to 1)
    category_scores = score_categories_with_llm(query, list(categories))
    
    # Store in context for downstream confidence scoring
    query_context["category_scores"] = category_scores

    boosted = []
    for doc in candidates:
        base_score = doc.get("score", 1.0)
        # Helper to extract string from potential dict
        def extract_cat_str(val):
            if isinstance(val, dict):
                return str(val.get("category") or val.get("value") or "").lower()
            return str(val or "").lower()

        cat_val = doc.get("category") or doc.get("inferred_category")
        cat = extract_cat_str(cat_val)

        # Get boost (default to 0.5 neutral if unknown, or 1.0? User said "irrelevant near 0")
        # Fail safe was 1.0. Let's use get(cat, 0.5) for unknown
        boost = category_scores.get(cat, 0.5) 
        
        doc["boosted_score"] = base_score * boost 
        doc["_category_boost"] = boost # Pass to reranker
        boosted.append(doc)

    # Sort by boosted score for immediate utility
    boosted.sort(key=lambda x: x["boosted_score"], reverse=True)
    return boosted

def lexical_search(collection, query_text, limit=50):
    results = list(collection.find(
        {
            "$or": [
                {"keywords": {"$regex": query_text, "$options": "i"}},
                {"entities.text": {"$regex": query_text, "$options": "i"}},
                {"translated_title": {"$regex": query_text, "$options": "i"}},
                {"title": {"$regex": query_text, "$options": "i"}}
            ],
            "status": {"$in": ["partial", "fully_analyzed"]}
        }
    ).limit(limit))
    
    for doc in results:
        doc["lexical_match"] = True
    return results

def fuse_results(vector_docs, lexical_docs):
    fused = {}

    # Vector results dominate recall (using previously retrieved structured results as vector proxy)
    for doc in vector_docs:
        fused[str(doc["_id"])] = {
            **doc,
            "score": doc.get("score", 1.0) * 0.7
        }

    # Lexical results add precision
    for doc in lexical_docs:
        doc_id = str(doc["_id"])
        if doc_id in fused:
            fused[doc_id]["score"] += 0.3
        else:
            fused[doc_id] = {
                **doc,
                "score": 0.3
            }

    return sorted(fused.values(), key=lambda x: x["score"], reverse=True)

def retrieve_candidates(processed_query: dict, limit: int = 50) -> list:
    """
    Brain-first retrieval with Hybrid Logic (Structured/Vector + Lexical Fusion).
    """
    db = current_app.db
    # articles = db.articles
    articles = db.news_dataset
    
    # Defensive check on processed_query
    if isinstance(processed_query, list):
        processed_query = processed_query[0] if processed_query else {}
    if not isinstance(processed_query, dict):
        processed_query = {}

    status_filter = {"status": {"$in": ["partial", "fully_analyzed"]}}

    # Extract Signals
    entities = processed_query.get("entities") or {}
    if not isinstance(entities, dict): entities = {}
    
    suggested_filters = processed_query.get("suggested_filters") or {}
    if not isinstance(suggested_filters, dict): suggested_filters = {}

    countries = suggested_filters.get("country") or []
    if isinstance(countries, str): countries = [countries]
    
    categories = suggested_filters.get("category") or []
    if isinstance(categories, str): categories = [categories]
    
    # CATEGORY MAPPING: Translate LLM suggestions to actual DB categories
    # Database has: ['aircraft', 'disaster', 'infrastructure', 'terror']
    CATEGORY_MAP = {
        'transportation': 'infrastructure',
        'transport': 'infrastructure',
        'roads': 'infrastructure',
        'highways': 'infrastructure',
        'construction': 'infrastructure',
        'building': 'infrastructure',
        'development': 'infrastructure',
        'security': 'terror',
        'attack': 'terror',
        'terrorism': 'terror',
        'violence': 'terror',
        'natural disaster': 'disaster',
        'earthquake': 'disaster',
        'flood': 'disaster',
        'storm': 'disaster',
        'aviation': 'aircraft',
        'flight': 'aircraft',
        'plane': 'aircraft',
        'airport': 'aircraft'
    }
    
    # Map categories to actual DB values
    mapped_categories = []
    for cat in categories:
        cat_lower = str(cat).lower()
        # Check if it's already a valid category
        if cat_lower in ['aircraft', 'disaster', 'infrastructure', 'terror']:
            mapped_categories.append(cat_lower)
        # Otherwise try to map it
        elif cat_lower in CATEGORY_MAP:
            mapped_categories.append(CATEGORY_MAP[cat_lower])
            print(f"📋 Mapped category '{cat}' → '{CATEGORY_MAP[cat_lower]}'")
        else:
            # Unknown category - include it anyway (might match)
            mapped_categories.append(cat_lower)
    
    categories = list(set(mapped_categories))  # Remove duplicates
    
    continent = entities.get("continent")
    time_window_days = processed_query.get("time_window_days")
    # Build Filters (for both Vector Pre-filtering and Structured fallback)
    structured_or = []
    
    # Pre-filter for Vector Search (Atlas supports $in for filter fields)
    vector_filter = {"status": {"$in": ["partial", "fully_analyzed"]}}

    if categories:
        # Vector filter: Use $in with lowercase (Atlas vector search requirement)
        cat_list = [str(c).lower() for c in categories]
        vector_filter["category"] = {"$in": cat_list}
        
        # Structured filter: Use case-insensitive regex for flexibility
        cat_regex = "|".join([re.escape(c) for c in cat_list])
        structured_or.append({"category": {"$regex": cat_regex, "$options": "i"}})
        print(f"🔍 Category filter: {cat_list}")

    if countries:
        # Vector filter: Use $in with lowercase
        norm_countries = [str(c).lower() for c in countries]
        
        # 🌏 RELAX: Always include 'global' news when looking for specific countries
        if "global" not in norm_countries:
            norm_countries.append("global")
            
        if any(c in norm_countries for c in ["usa", "us", "united states"]):
            norm_countries.extend(["americas"])
        vector_filter["country"] = {"$in": norm_countries}
        
        # Structured filter: Use case-insensitive regex
        country_regex = "|".join([re.escape(c) for c in norm_countries])
        structured_or.append({"country": {"$regex": country_regex, "$options": "i"}})
        print(f"🌍 Country filter (Relaxed): {norm_countries}")

    if continent:
        # Vector filter: Use exact match with lowercase
        continent_lower = str(continent).lower()
        vector_filter["continent"] = continent_lower
        
        # Structured filter: Use case-insensitive regex
        structured_or.append({"continent": {"$regex": re.escape(continent_lower), "$options": "i"}})

    # ---------------------------
    # Stream 1: AI Vector Search (Semantic)
    # ---------------------------
    query_text = processed_query.get("canonical_query") or processed_query.get("original_query") or ""
    vector_docs = []
    
    # Try high-accuracy vector search with metadata pre-filtering (using HyDE)
    if query_text:
        # Generate hypothetical answer to align query semantics with manual news articles
        llm = get_ollama_llm()
        hyde_text = generate_hypothetical_answer(query_text, llm)
        
        # Safety fallback
        if not hyde_text or len(hyde_text) < 20:
            hyde_text = query_text
            
        print(f"HyDE Output: {hyde_text}")
        
        # We pass the vector_filter to ensure we search ONLY within relevant topics/locations
        vector_docs = vector_search(hyde_text, limit=limit, pre_filter=vector_filter)
    
    # 1B. Fallback with Structured search if vector search is empty or filtered too strictly
    if not vector_docs and structured_or:
        base_query = {
            "$and": [
                status_filter,
                {"$or": structured_or}
            ]
        }
        
        # Apply Time Filter to Structured fallback
        if time_window_days:
            cutoff = datetime.utcnow() - timedelta(days=time_window_days)
            time_query = {
                "$and": base_query["$and"] + [{"created_at": {"$gte": cutoff}}]
            }
            vector_docs = list(articles.find(time_query).sort("published_date", -1).limit(limit))
            # Fallback if time query yields nothing
            if not vector_docs:
                vector_docs = list(articles.find(base_query).sort("published_date", -1).limit(limit))
        else:
             vector_docs = list(articles.find(base_query).sort("published_date", -1).limit(limit))

    for doc in vector_docs:
        doc["semantic_match"] = True

    # ---------------------------
    # Stream 2: Lexical Search (Keyword Exact Match)
    # ---------------------------
    query_text = processed_query.get("canonical_query") or processed_query.get("original_query") or ""
    lexical_docs = lexical_search(articles, query_text, limit=limit)

    # ---------------------------
    # Stream 3: Fusion & Safety Net
    # ---------------------------
    if not vector_docs and not lexical_docs:
        # Final Safety Net: Recent News
        recent_cutoff = datetime.utcnow() - timedelta(days=14)
        query = {
            "$and": [
                status_filter,
                {"created_at": {"$gte": recent_cutoff}}
            ]
        }
        vector_docs = list(articles.find(query).sort("published_date", -1).limit(10))

    # Fuse Results
    candidates = fuse_results(vector_docs, lexical_docs)
    
    # Apply Dynamic Category Boosting
    return apply_dynamic_category_boost(candidates, processed_query)

"""
News Routes
Endpoints for real-time data ingestion
"""

import logging
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId

from app.services.discovery.news_fetcher import news_fetcher_service
from app.services.discovery.fetch.resolver import resolve_context
from app.services.analysis.translation_service import translation_service
from app.utils.language import decide_second_language, translate_analysis_additive, get_or_create_translated_analysis
from app.coordinator import get_coordinator

logger = logging.getLogger(__name__)
news_bp = Blueprint('news', __name__)


# ---------------------------------------------------------
# HELPER: GENERIC MISSING CHECK (UNCHANGED)
# ---------------------------------------------------------

def is_missing(value):
    return value is None or value == "" or value == []


def get_missing_analysis_stages(doc):
    missing = []

    if is_missing(doc.get("raw_text")):
        missing.append("raw_text")

    if is_missing(doc.get("summary")):
        missing.append("summary")

    if is_missing(doc.get("sentiment")):
        missing.append("sentiment")

    if is_missing(doc.get("keywords")):
        missing.append("keywords")

    if is_missing(doc.get("entities")):
        missing.append("entities")

    if is_missing(doc.get("event")):
        missing.append("event")

    if is_missing(doc.get("locations")):
        missing.append("locations")

    return missing


# ---------------------------------------------------------
# LIST STORED NEWS (LEVEL-1 FEED) — UNCHANGED
# ---------------------------------------------------------

@news_bp.route('/list-new-news', methods=['GET'])
@jwt_required()
def list_news():
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        skip = (page - 1) * limit

        db = current_app.db
        query = {
            "status": {"$in": ["partial", "fully_analyzed"]}
        }  # Only show processed articles

        category = request.args.get('category')
        sub_category = request.args.get('sub_category')

        if category:
            query['category'] = category

        if sub_category:
            query['sub_category'] = sub_category

        # total = db.articles.count_documents(query)
        total = db.news_dataset.count_documents(query)

        cursor = (
            # db.articles
            db.news_dataset
            .find(query)
            .sort([('published_date', -1), ('_id', -1)])
            .skip(skip)
            .limit(limit)
        )

        articles = []
        for doc in cursor:
            articles.append({
                'id': str(doc['_id']),
                'title': doc.get('title'),
                'source': doc.get('source'),
                'original_url': doc.get('original_url'),
                'published_date': doc.get('published_date'),
                'summary': doc.get('summary'),
                'category': doc.get('category'),
                'analyzed': doc.get('analyzed', False)
            })

        return jsonify({
            'status': 'success',
            'data': {
                'articles': articles,
                'pagination': {
                    'total': total,
                    'page': page,
                    'limit': limit,
                    'pages': (total + limit - 1) // limit
                }
            }
        }), 200

    except Exception as e:
        logger.error(f"News list error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ---------------------------------------------------------
# GET SINGLE ARTICLE (LEVEL-1)
# ---------------------------------------------------------

@news_bp.route('/article/<doc_id>', methods=['GET'])
@jwt_required()
def get_article(doc_id):
    try:
        db = current_app.db
        # doc = db.articles.find_one({'_id': ObjectId(doc_id)})
        doc = db.news_dataset.find_one({'_id': ObjectId(doc_id)})
        
        if not doc:
            return jsonify({'status': 'error', 'message': 'Article not found'}), 404
            
        return jsonify({
            'status': 'success',
            'article': {
                'id': str(doc['_id']),
                '_id': str(doc['_id']),
                'title': doc.get('title'),
                'source': doc.get('source'),
                'original_url': doc.get('original_url'),
                'image_url': doc.get('image_url'),
                'published_date': doc.get('published_date'),
                'summary': doc.get('summary') or doc.get('rss_summary'),
                'category': doc.get('category'),
                'analyzed': doc.get('analyzed', False)
            }
        }), 200
    except Exception as e:
        logger.error(f"Get article error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ---------------------------------------------------------
# CATEGORY-BASED FETCH (LEVEL-1) 
# ---------------------------------------------------------

@news_bp.route('/fetch-category', methods=['GET'])
@jwt_required()
def fetch_category_news():
    try:
        category = request.args.get('category')
        if not category:
            return jsonify({
                'status': 'error',
                'message': 'category query parameter is required'
            }), 400

        user_id = get_jwt_identity()
        db = current_app.db

        # Map old API to new fetch_news
        # Don't hardcode language - let it be inferred or empty
        context = {
            "category": category.lower(),
            "language": [],  # Empty - no language filtering
            "language_source": "none",
            "country": "unknown",
            "continent": "unknown",
            "scope": "global"
        }

        result = news_fetcher_service.fetch_news_with_context(
            db=db,
            user_id=user_id,
            context=context,
            query_language=None  # No language filtering
        )

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Category fetch error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to fetch category news: {str(e)}'
        }), 500


# ---------------------------------------------------------
# UNIFIED DEEP INTELLIGENCE AUDIT
# ---------------------------------------------------------

@news_bp.route('/analyze/<doc_id>', methods=['GET'])
@jwt_required()
def analyze_news_item(doc_id):
    """
    User-triggered full intelligence audit.
    Runs the complete DAG pipeline including context categorization,
    spatial mapping, and sentiment pulse.
    """
    # ⏸ Enter priority mode to pause all background tasks during intensive AI analysis
    coordinator = get_coordinator()
    coordinator.enter_priority_mode()
        
    try:
        db = current_app.db

        # ALWAYS run FULL pipeline when user clicks "Run Deep Analysis"
        # 🔒 ATOMIC LOCK: Only proceed if status is not already 'processing'
        doc = db.news_dataset.find_one_and_update(
            {
                "_id": ObjectId(doc_id),
                "status": {"$ne": "processing"}
            },
            {
                "$set": {"status": "processing"}
            },
            return_document=True
        )

        if not doc:
            # Check if it was because it's already processing or doesn't exist
            existing = db.news_dataset.find_one({"_id": ObjectId(doc_id)})
            if not existing:
                return jsonify({"status": "error", "message": "Article not found"}), 404
            
            return jsonify({
                "status": "processing",
                "message": "Analysis is already in progress for this article."
            }), 202
        # No cache - user explicitly requested fresh analysis
        # Only log if NOT in visual mode to keep terminal clean
        if not current_app.config.get("DEBUG", False): 
            logger.info(f"[{doc_id}] Running FULL pipeline (user-triggered analysis)")
        
        # Check if we have either raw_text OR a URL we can scrape
        raw_text = doc.get("raw_text", "")
        original_url = doc.get("original_url", "")
        
        if not raw_text and not original_url:
            return jsonify({"status": "error", "message": "No article content or URL available for analysis"}), 400
        
        # Run FULL pipeline (stages=None means run ALL stages)
        # This will internally scrape the URL if raw_text is missing
        result = news_fetcher_service.scrape_and_analyze_article(
            db=db,
            doc_id=doc_id,
            stages=None,  # ← KEY: None = run complete pipeline including sentiment, summary, location
            visual=True   # ← Enable Clean Visual Logging
        )
        
        if result and result.get("success") is False:
            return jsonify({
                "status": "error",
                "message": result.get("error", "Analysis failed"),
                "failed_gate": result.get("failed_gate")
            }), 400

        # Update status to fully_analyzed
        db.news_dataset.update_one(
            {"_id": ObjectId(doc_id)},
            {"$set": {"status": "fully_analyzed", "analyzed": True}}
        )
        
        # doc = db.articles.find_one({"_id": ObjectId(doc_id)})
        doc = db.news_dataset.find_one({"_id": ObjectId(doc_id)})

        meta = doc.get("metadata", {})

        published_date = meta.get("published_date")
        published_at = (
            published_date.isoformat()
            if hasattr(published_date, "isoformat")
            else published_date
        )
        response_data = {
            "status": "success",
            "document_id": str(doc["_id"]),
            "article": {
                "title": meta.get("title", doc.get("title", "Untitled")),
                "original_url": meta.get("original_url", doc.get("original_url", "")),
                "source": meta.get("publisher", doc.get("source", "")),
                "published_at": published_at,
                "language": doc.get("language", "unknown")
            },
            "content": {
                "raw": doc.get("raw_text", ""),
                "cleaned": doc.get("cleaned_text", "")
            },
            "summary": {
                "text": (doc.get("summary", "") if isinstance(doc.get("summary"), str) 
                         else doc.get("summary", {}).get("en", "")),
                "method": "bart-v2",
                "sentences": 3
            },
            "analysis": {
                "sentiment": doc.get("sentiment") or {
                    "label": "neutral",
                    "confidence": 0.0,
                    "method": "fallback"
                },
                "event": doc.get("event") or {
                    "type": "other",
                    "confidence": 0.0,
                    "method": "fallback"
                },
                "location": doc.get("locations") if doc.get("locations") and any(doc["locations"].values()) else {
                    "status": "not_detected",
                },
                "keywords": doc.get("keywords", []),
                "entities": doc.get("entities", [])
            }
        }

        # 🔹 Multi-Language Response Architecture (Additive)
        article_lang = doc.get("language")
        second_lang = decide_second_language(article_lang)

        if second_lang:
            try:
                # Use current analysis as source
                analysis_en = response_data["analysis"]
                
                # Use read-through cache
                translated_data = get_or_create_translated_analysis(
                    doc=doc,
                    analysis_en={
                        "summary": response_data["summary"]["text"],
                        **analysis_en
                    },
                    target_lang=second_lang,
                    translator_service=translation_service,
                    # collection=db.articles,
                    collection=db.news_dataset,
                    logger=logger
                )
                
                response_data["analysis_translated"] = {
                    second_lang: translated_data
                }
            except Exception as te:
                logger.error(f"Additive translation failed for {second_lang}: {te}")

        return jsonify(response_data), 200

    except Exception as e:
        logger.exception("Level-2 analysis failed")
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        # ▶ Exit priority mode and resume background tasks
        coordinator = get_coordinator()
        coordinator.exit_priority_mode()


# ---------------------------------------------------------
# FULL VIEW (LEVEL-2) — UNCHANGED
# ---------------------------------------------------------

@news_bp.route('/<doc_id>/full-view', methods=['GET'])
@jwt_required()
def get_news_full_view(doc_id):
    try:
        db = current_app.db

        # Check in articles collection first
        # doc = db.articles.find_one({'_id': ObjectId(doc_id)})
        doc = db.news_dataset.find_one({'_id': ObjectId(doc_id)})
        if not doc:
            # Fallback to documents
            doc = db.documents.find_one({'_id': ObjectId(doc_id)})
            
        if not doc:
            return jsonify({'status': 'error', 'message': 'Not found'}), 404

        meta = doc.get('metadata', {})

        return jsonify({
            'status': 'success',
            'data': {
                'article': {
                    'id': str(doc['_id']),
                    'title': meta.get('title'),
                    'content': doc.get('raw_text'),
                    'source': meta.get('publisher'),
                    'resolved_url': meta.get('resolved_url'),
                    'thumbnail_image_url': meta.get('thumbnail_image_url'),
                    'article_image_url': meta.get('article_image_url')
                },
                'analysis': {
                    'sentiment': doc.get('sentiment') or {
                        'label': 'neutral',
                        'confidence': 0.0,
                        'method': 'fallback'
                    },
                    'location': doc.get('location'),
                    'event_type': doc.get('event_type')
                },
                'reactions': []
            }
        }), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@news_bp.route('/fetch', methods=['GET'])
@jwt_required()
def fetch_news_with_params():
    """
    NEW unified fetching API.
    Uses resolver + param-based fetching.
    Does NOT affect existing APIs.
    """
    try:
        params = request.args.to_dict()
        user_id = get_jwt_identity()
        db = current_app.db

        # Extract user-provided parameters separately
        def get_arg_list(key):
            val = request.args.getlist(key)
            if not val:
                v = request.args.get(key)
                if v: val = [v]
            return val

        query_language = get_arg_list("language")
        query_continents = get_arg_list("continent")
        query_countries = get_arg_list("country")
        query_sources = get_arg_list("source")
        keyword = request.args.get("q") or request.args.get("keyword")

        # 🔹 Resolve context (for analytics/UI)
        # We pass request.args directly because resolve_context now handles MultiDict/dict correctly
        context = resolve_context(request.args, db=db)
        
        # Override context lists if provided
        if query_continents: context["continent"] = query_continents
        if query_countries: context["country"] = query_countries
        if query_sources: context["source"] = query_sources
        if query_language: context["language"] = query_language

        # Debug logging
        logger.info(f"[fetch] query_language={query_language}, continents={query_continents}, countries={query_countries}, sources={query_sources}")

        # 🔹 Fetch news using new logic (pass query_language separately)
        result = news_fetcher_service.fetch_news_with_context(
            db=db,
            user_id=user_id,
            context=context,
            query_language=query_language,
            keyword=keyword
        )

        return jsonify({
            "status": "success",
            "context": context,
            **result
        }), 200

    except Exception as e:
        logger.exception("Param-based fetch failed")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# ---------------------------------------------------------
# KEYWORD SEARCH (NEW - Two-Phase System)
# ---------------------------------------------------------

@news_bp.route('/keyword-search', methods=['GET'])
@jwt_required()
def keyword_search():
    """
    Keyword-based news search across processed articles.
    Searches keywords, entities, and clean text fields.
    Works with multilingual queries.
    """
    try:
        from langdetect import detect
        
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({"status": "error", "message": "Query parameter 'q' is required"}), 400
        
        limit = min(int(request.args.get('limit', 20)), 100)
        page = max(int(request.args.get('page', 1)), 1)
        skip = (page - 1) * limit
        
        # Detect query language
        try:
            detected_lang = detect(query)
        except:
            detected_lang = 'en'
        
        logger.info(f"Keyword search: query='{query}', detected_lang={detected_lang}, limit={limit}")
        
        db = current_app.db
        
        # Build search query - only search processed articles
        search_conditions = []
        
        # Search in keywords (both original and English)
        search_conditions.append({"keywords": {"$regex": query, "$options": "i"}})
        
        # Search in entity texts
        search_conditions.append({"entities.text": {"$regex": query, "$options": "i"}})
        
        # Search in clean_text
        search_conditions.append({"cleaned_text": {"$regex": query, "$options": "i"}})
        
        # Search in title
        search_conditions.append({"title": {"$regex": query, "$options": "i"}})
        
        # Main query: match any search condition AND status is partial or fully_analyzed
        mongo_query = {
            "$and": [
                {"$or": search_conditions},
                {"status": {"$in": ["partial", "fully_analyzed"]}}  # Only search processed articles
            ]
        }
        
        # Execute search
        # results = list(db.articles.find(mongo_query).sort("published_date", -1).skip(skip).limit(limit))
        # total = db.articles.count_documents(mongo_query)
        results = list(db.news_dataset.find(mongo_query).sort("published_date", -1).skip(skip).limit(limit))
        total = db.news_dataset.count_documents(mongo_query)
        
        # Format results
        articles = []
        for doc in results:
            # Calculate simple relevance score
            relevance_score = 0
            query_lower = query.lower()
            
            # Title match (highest weight)
            if query_lower in doc.get("title", "").lower():
                relevance_score += 5
            
            # Keywords match
            keywords = doc.get("keywords", [])
            if isinstance(keywords, list):
                for kw in keywords:
                    if query_lower in kw.lower():
                        relevance_score += 3
                        break
            
            # Entity match
            entities = doc.get("entities", [])
            if isinstance(entities, list):
                for ent in entities:
                    if query_lower in ent.get("text", "").lower():
                        relevance_score += 2
                        break
            
            # Text match
            if query_lower in doc.get("cleaned_text", "").lower():
                relevance_score += 1
            
            articles.append({
                "_id": str(doc["_id"]),
                "title": doc.get("title"),
                "source": doc.get("source"),
                "published_date": doc.get("published_date"),
                "summary": doc.get("summary") or doc.get("rss_summary"),
                "image_url": doc.get("image_url"),
                "original_url": doc.get("original_url"),  # Added for direct article access
                "category": doc.get("category"),
                "relevance_score": relevance_score,
                "status": doc.get("status")
            })
        
        # Sort by relevance
        articles.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        return jsonify({
            "status": "success",
            "query": query,
            "detected_language": detected_lang,
            "total": total,
            "page": page,
            "limit": limit,
            "articles": articles
        }), 200
        
    except Exception as e:
        logger.exception("Keyword search failed")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# ---------------------------------------------------------
# BACKGROUND WORKER CONTROL (NEW)
# ---------------------------------------------------------

@news_bp.route('/worker/status', methods=['GET'])
@jwt_required()
def worker_status():
    """Get background worker status"""
    try:
        if hasattr(current_app, 'background_worker'):
            worker = current_app.background_worker
            return jsonify({
                "status": "success",
                "worker": {
                    "running": worker.running,
                    "batch_size": 3,
                    "sleep_interval": 30
                }
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "Background worker not initialized"
            }), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@news_bp.route('/worker/pause', methods=['POST'])
@jwt_required()
def worker_pause():
    """Pause the background worker"""
    try:
        if hasattr(current_app, 'background_worker'):
            worker = current_app.background_worker
            worker.running = False
            logger.info("⏸ Background worker paused by user")
            return jsonify({
                "status": "success",
                "message": "Background worker paused"
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "Background worker not initialized"
            }), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@news_bp.route('/worker/resume', methods=['POST'])
@jwt_required()
def worker_resume():
    """Resume the background worker"""
    try:
        if hasattr(current_app, 'background_worker'):
            worker = current_app.background_worker
            worker.running = True
            logger.info("▶ Background worker resumed by user")
            return jsonify({
                "status": "success",
                "message": "Background worker resumed"
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "Background worker not initialized"
            }), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ---------------------------------------------------------
# DEBUG: INTELLINEWS SEARCH RETRIEVER TEST
# ---------------------------------------------------------

@news_bp.route('/_debug/intelli-retriever', methods=['GET'])
def debug_retriever():
    """
    Debug endpoint to test IntelliNews Search retriever.
    Usage: GET /api/news/_debug/intelli-retriever?q=roads+in+china
    """
    from app.services.intelli_search.query_processor import process_query
    from app.services.intelli_search.retriever import retrieve_candidates
    
    query_text = request.args.get('q', 'roads in china bad')
    
    try:
        # Process query with Ollama
        processed_query = process_query(query_text)
        
        # Retrieve candidates from MongoDB
        docs = retrieve_candidates(processed_query)
        
        return jsonify({
            "status": "success",
            "query": processed_query,
            "count": len(docs),
            "sample_titles": [d.get("title") for d in docs[:5]],
            "sample_sources": [d.get("source") for d in docs[:5]]
        }), 200
    except Exception as e:
        logger.exception("Debug retriever failed")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# ---------------------------------------------------------
# DEBUG: INTELLINEWS SEARCH RERANKER TEST
# ---------------------------------------------------------

@news_bp.route("/_debug/intelli-rerank", methods=["GET"])
def debug_rerank():
    """
    Debug endpoint to test the full IntelliNews Search pipeline including reranking.
    Usage: GET /api/news/_debug/intelli-rerank?q=trump+modi
    """
    from app.services.intelli_search.query_processor import process_query
    from app.services.intelli_search.retriever import retrieve_candidates
    from app.services.intelli_search.reranker import rerank

    query_text = request.args.get('q', 'trump modi')
    
    try:
        # 1. Query Understanding
        q_signals = process_query(query_text)
        
        # 2. Broad Retrieval
        docs = retrieve_candidates(q_signals)
        
        # 3. Precision Reranking
        ranked = rerank(q_signals["original_query"], docs)

        return jsonify({
            "query": q_signals,
            "before_count": len(docs),
            "after_count": len(ranked),
            "before_titles": [d.get("title") for d in docs],
            "after_titles": [d.get("title") for d in ranked]
        }), 200
    except Exception as e:
        logger.exception("Debug rerank failed")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
@news_bp.route('/pipeline-status/<doc_id>', methods=['GET'])
@jwt_required()
def get_pipeline_status(doc_id):
    """
    Track the 8-stage NLP pipeline progress for a specific article.
    Used for the frontend real-time progress bar.
    """
    try:
        db = current_app.db
        # doc = db.articles.find_one({"_id": ObjectId(doc_id)})
        doc = db.news_dataset.find_one({"_id": ObjectId(doc_id)})
        
        if not doc:
            return jsonify({"status": "error", "message": "Article not found"}), 404
            
        # 8-Stage Pipeline Mapping
        stages = [
            {"id": "deduplication", "label": "Deduplication", "field": "_id"},
            {"id": "scraping", "label": "Deep Scraping", "field": "raw_text"},
            {"id": "language", "label": "Language Detection", "field": "language"},
            {"id": "classification", "label": "Event Classification", "field": "event"},
            {"id": "localization", "label": "Multi-Layer localization", "field": "locations"},
            {"id": "summarization", "label": "Contextual Summary", "field": "summary"},
            {"id": "entities", "label": "Entity Detection", "field": "entities"},
            {"id": "sentiment", "label": "Sentiment Analysis", "field": "sentiment"}
        ]
        
        completed_stages = 0
        current_stage_label = "Initializing..."
        
        for stage in stages:
            field_val = doc.get(stage["field"])
            # Special check for locations dict
            if stage["id"] == "localization":
                is_done = field_val and any(field_val.values())
            # Special check for event dict
            elif stage["id"] == "classification":
                is_done = field_val and field_val.get("type") and field_val.get("type") != "other"
            else:
                is_done = not is_missing(field_val)
            
            if is_done:
                completed_stages += 1
            else:
                current_stage_label = stage["label"] + "..."
                break
        
        # Calculate percentage
        progress = int((completed_stages / len(stages)) * 100)
        
        # If status is fully_analyzed, force 100%
        if doc.get("status") == "fully_analyzed":
            progress = 100
            current_stage_label = "Analysis Complete"

        return jsonify({
            "status": "success",
            "data": {
                "progress": progress,
                "current_stage": current_stage_label,
                "is_complete": progress == 100,
                "status": doc.get("status", "pending")
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Pipeline status error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

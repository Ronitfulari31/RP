from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
import logging
import numpy as np
from app.services.intelli_search.query_processor import process_query
from app.services.intelli_search.retriever import retrieve_candidates
from app.services.intelli_search.reranker import rerank
from app.services.intelli_search.confidence import compute_confidence
from app.services.intelli_search.explainer import explain_result

def convert_numpy_types(obj):
    """Recursively convert numpy types to Python native types for JSON serialization."""
    if isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif hasattr(obj, 'item'):  # Catch any numpy scalar
        return obj.item()
    return obj

logger = logging.getLogger(__name__)
intelli_search_bp = Blueprint('intelli_search', __name__)

@intelli_search_bp.route('/search', methods=['POST'])
@jwt_required()
def search():
    """
    High-accuracy intelligent search endpoint.
    Expects JSON: {"query": "natural language query"}
    """
    data = request.get_json()
    if not data or not data.get('query'):
        return jsonify({"status": "error", "message": "Query is required"}), 400
    
    query_text = data.get('query')
    
    # 🎯 PRIORITY MODE: Pause background services for dedicated search resources
    scheduler = getattr(current_app, 'scheduler', None)
    worker = getattr(current_app, 'background_worker', None)
    
    services_paused = False
    try:
        if scheduler:
            scheduler.pause()
            logger.info("⏸️  RSS Scheduler paused for IntelliSearch")
        if worker and hasattr(worker, 'pause'):
            worker.pause()
            logger.info("⏸️  NLP Worker paused for IntelliSearch")
        services_paused = True
    except Exception as e:
        logger.warning(f"Could not pause background services: {e}")
    
    try:
        # 1. Query Understanding (Ollama)
        q_signals = process_query(query_text)
        
        # Log multi-intent detection (Phase 10)
        if q_signals.get("decomposition", {}).get("is_multi_intent"):
            logger.info(f"🔀 Multi-intent detected: {query_text}")
            logger.info(f"   Sub-queries: {q_signals['decomposition']['sub_queries']}")
            logger.info(f"   Reason: {q_signals['decomposition']['reason']}")
        
        # 🎯 Detect broad category queries (e.g., "all disaster news")
        from app.services.intelli_search.reranker import is_broad_category_query
        is_broad_query = is_broad_category_query(query_text, q_signals)
        
        # 2. Broad Retrieval (MongoDB)
        # For broad queries, retrieve more candidates; for specific queries, 50 is enough
        retrieval_limit = 200 if is_broad_query else 50
        candidates = retrieve_candidates(q_signals, limit=retrieval_limit)
        
        if not candidates:
            return jsonify({
                "status": "success",
                "results": [],
                "meta": {
                    "count": 0,
                    "query_signals": q_signals,
                    "reason": "No relevant articles found"
                }
            }), 200
            
        # 3. Precision Reranking (Now uses v1.0-search: FlashRank + BGE)
        # For broad queries, return more results
        top_k = 50 if is_broad_query else 10
        ranked_results = rerank(query_text, candidates, top_k=top_k, q_signals=q_signals)
        
        # Serialize MongoDB documents
        serialized_results = []
        for doc in ranked_results:
            # Ensure _id is string
            doc['_id'] = str(doc['_id'])
            
            # Attach explanations and scores
            doc["explanation"] = explain_result(doc, q_signals)
            
            # Ensure scores are Python native floats (not numpy float32)
            bge_score = doc.get("bge_score", 0)
            flash_score = doc.get("_flash_score", 0)
            
            # Convert numpy types to Python native types
            doc["bge_score"] = float(bge_score.item() if hasattr(bge_score, 'item') else bge_score)
            doc["flash_score"] = float(flash_score.item() if hasattr(flash_score, 'item') else flash_score)
            
            serialized_results.append(doc)
            
        # 4. Confidence Scoring
        confidence_info = compute_confidence(ranked_results, q_signals)
        
        # Meta dictionary
        meta = {
            "count": len(serialized_results),
            "query_signals": q_signals,
            **confidence_info
        }

        # Step 4 — Fallback behavior if confidence is low
        if confidence_info["confidence"] < 0.35:
            meta["fallback"] = "Expanded search scope due to low confidence"

        response_data = {
            "status": "success",
            "results": serialized_results,
            "meta": meta
        }
        
        return jsonify(convert_numpy_types(response_data)), 200
        
    except Exception as e:
        logger.exception("IntelliNews Search failed")
        
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    
    finally:
        # 🎯 PRIORITY MODE: Resume background services after search completes
        if services_paused:
            try:
                if scheduler:
                    scheduler.resume()
                    logger.info("▶️  RSS Scheduler resumed after IntelliSearch")
                if worker and hasattr(worker, 'resume'):
                    worker.resume()
                    logger.info("▶️  NLP Worker resumed after IntelliSearch")
            except Exception as e:
                logger.warning(f"Could not resume background services: {e}")

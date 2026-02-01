"""
Unified Intelligence Pipeline
-----------------------------
Orchestrates documents through the high-accuracy DAG engine.
This handles background RSS news, manual uploads, and deep analysis.
"""

import logging
import time
import unicodedata
from bson import ObjectId
from datetime import datetime

logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# CORE PIPELINE ENTRY POINT (DAG-Based Engine)
# ---------------------------------------------------------

def process_document_pipeline(db, doc_id, raw_text, stages=None, collection="documents", visual=False):
    """
    Standard entry point for all document analysis in the system.
    Orchestrates the flow through the Version 2 (DAG) architecture.
    """
    from app.services.dag.definitions.nlp_pipeline_v2 import build_nlp_pipeline
    from app.services.dag.context import create_initial_context
    from app.models.document import Document
    
    start_time = time.time()
    if not visual:
        logger.info(f"[{doc_id}] \u25b6 Starting Unified Pipeline | Collection: {collection}")
    
    try:
        # 1. Fetch document metadata for context (language, category, title)
        doc = db[collection].find_one({"_id": ObjectId(doc_id)})
        if not doc:
            return {"success": False, "error": "Document not found"}

        # 2. Map legacy 'stages' to V2 'processing_mode'
        # Decided based on the presence of high-intensity analysis keys
        mode = "full"
        if stages:
            # Check for: sentiment, summary (These are the only 'Heavy' stages now)
            has_heavy = any(s in stages for s in ["sentiment", "summary"])
            if not has_heavy:
                mode = "reduced"
        
        # NOTE: Embeddings now run in BOTH 'full' and 'reduced' modes automatically.

        # 3. Create initial context with metadata parity
        context = create_initial_context(
            document_id=str(doc_id),
            raw_text=raw_text,
            db=db,  # Pass database for entity learning
            metadata={
                "title": doc.get("title", ""),
                "language": doc.get("language"),
                "category": doc.get("category"),
                "source": doc.get("source"),
                "collection": collection,
                "processing_mode": mode,
                "existing_keywords": doc.get("keywords", []),
                "existing_entities": doc.get("entities", []),
                "existing_category": doc.get("category"),
                "existing_category_conf": doc.get("scores", {}).get("category_confidence", 0.0),
                "existing_locations": doc.get("locations"),
                "existing_sentiment": doc.get("sentiment"),
                "existing_summary": doc.get("summary")
            }
        )
        
        # 4. Build and Run DAG
        executor = build_nlp_pipeline()
        final_context = executor.run(context, visual=visual)
        
        if final_context.get("rejected"):
            logger.warning(f"[{doc_id}] \u274c Pipeline Rejected: {final_context.get('rejection_reason')}")
            return {
                "success": False, 
                "status": "rejected",
                "reason": final_context.get("rejection_reason"),
                "failed_gate": final_context.get("failed_gate"),
                "stats": {"reduction_percentage": 0, "time_taken": round((time.time() - start_time), 2)}
            }

        # 5. Atomic Persistence
        # We'll use the robust model method which handles all keys correctly
        Document.update_from_dag_context(db, doc_id, final_context, collection=collection)
        
        total_time = (time.time() - start_time) * 1000
        logger.info(f"[{doc_id}] \u2705 Unified Pipeline Completed ({total_time:.0f}ms)")
        
        # 6. Dual Language Response Construction
        # If the detected language is NOT English, we must provide both EN and NATIVE results.
        response_data = {
            "success": True, 
            "processing_time": total_time,
            "tier": final_context.get("tier"),
            "processing_path": final_context.get("processing_path"),
            "language": final_context.get("language"),
            "category": final_context.get("category"),
            "stats": {
                "reduction_percentage": final_context.get("scores", {}).get("reduction_percentage", 0.0),
                "time_taken": round(total_time / 1000, 2)
            }
        }

        # Base Analysis (English by default in strict pipeline)
        base_analysis = {
            "summary": final_context.get("summary"),
            "sentiment": final_context.get("sentiment"),
            "keywords": final_context.get("keywords"),
            "entities": final_context.get("entities"),
            "locations": final_context.get("locations")
        }

        detected_lang = final_context.get("language")
        
        # Hydrate Response with Dual Language Data
        if detected_lang and detected_lang != 'en' and detected_lang != 'unknown':
            try:
                from app.utils.language import translate_analysis_additive
                from app.services.analysis.translation_service import translation_service
                
                # Generate Native Translation
                native_analysis = translate_analysis_additive(
                    base_analysis, 
                    target_lang=detected_lang, 
                    translator=translation_service
                )

                # Structure: { en: ..., native: ... }
                response_data["summary"] = {
                    "en": base_analysis["summary"],
                    "native": native_analysis.get("summary")
                }
                response_data["keywords"] = {
                    "en": base_analysis["keywords"],
                    "native": native_analysis.get("keywords")
                }
                # For sentiment, we keep the object but translate the label/explanation if string
                response_data["sentiment"] = base_analysis["sentiment"]
                if native_analysis.get("sentiment"):
                     # Add native label to existing object
                     if "label" in native_analysis["sentiment"]:
                         response_data["sentiment"]["label_native"] = native_analysis["sentiment"]["label"]
                     if "sentiment" in native_analysis["sentiment"]:
                         response_data["sentiment"]["sentiment_native"] = native_analysis["sentiment"]["sentiment"]

                response_data["entities"] = {
                    "en": base_analysis["entities"],
                    "native": native_analysis.get("entities")
                }
                response_data["locations"] = base_analysis["locations"] # Locations usually universal or en

            except Exception as trans_e:
                logger.error(f"Dual language generation failed: {trans_e}")
                # Fallback to just English
                response_data.update(base_analysis)
        else:
            # English / Unknown -> Standard flat structure (Frontend handles this as 'en' default)
            response_data.update(base_analysis)
            # Ensure consistency for frontend that might check .en
            if isinstance(base_analysis["summary"], str):
                 response_data["summary"] = {"en": base_analysis["summary"]}
            if isinstance(base_analysis["keywords"], list):
                 response_data["keywords"] = {"en": base_analysis["keywords"]}

        return response_data

    except Exception as e:
        logger.exception(f"[{doc_id}] \u274c Unified Pipeline Failed")
        return {
            "success": False, 
            "error": str(e),
            "stats": {"reduction_percentage": 0, "time_taken": 0}
        }

# Re-expose helpers if needed by legacy callers (minimal set for maintenance)
def normalize_text(text: str) -> str:
    if not text:
        return ""
    return unicodedata.normalize("NFKC", text).strip()

import logging
from datetime import datetime
from bson import ObjectId

logger = logging.getLogger(__name__)

class RejectionLogger:
    """Service to log and persist pipeline rejections for audit and tuning."""

    @staticmethod
    def log_rejection(db, context: dict):
        doc_id = context.get("document_id")
        rejection_data = {
            "document_id": doc_id,
            "rejection_reason": context.get("rejection_reason"),
            "rejected_at_node": context.get("rejected_at_node"),
            "scores": context.get("scores"),
            "flags": context.get("flags"),
            "language": context.get("language"),
            "timestamp": datetime.utcnow()
        }

        logger.warning(f"Pipeline REJECTION for {doc_id}: {rejection_data['rejection_reason']} at {rejection_data['rejected_at_node']}")

        # Persist to a specialized collection for analysis
        try:
            db.pipeline_rejections.insert_one(rejection_data)
            
            # Update original document status if it exists
            if doc_id:
                db.documents.update_one(
                    {"_id": ObjectId(doc_id) if isinstance(doc_id, str) else doc_id},
                    {"$set": {
                        "status": "rejected",
                        "rejection_reason": context.get("rejection_reason"),
                        "analyzed": False,
                        "metadata.status": "failed",
                        "metadata.error": context.get("rejection_reason")
                    }}
                )
        except Exception as e:
            logger.error(f"Failed to persist rejection log: {e}")

# Singleton instance
rejection_logger = RejectionLogger()

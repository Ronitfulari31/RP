"""
Background NLP Worker
Processes RSS-fetched articles with partial pipeline for keyword search support.
Executes ONLY:
- Preprocessing
- Translation
- Keywords (RAKE)
- Entities (SpaCy NER)
- Event Classification (Zero-shot)
"""

import time
import logging
from datetime import datetime
from bson import ObjectId
from app import create_app
from app.services.core.pipeline_orchestrator import process_document_pipeline
from app.services.discovery.fetch.extraction import extract_article_package

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Worker configuration
BATCH_SIZE = 5  # Process 2-3 articles per iteration
SLEEP_INTERVAL = 30  # Sleep 30 seconds between batches
MAX_RETRIES = 3


class BackgroundNLPWorker:
    """
    Continuously processes pending articles with partial NLP pipeline.
    Articles are marked as "partial" after processing.
    """
    
    def __init__(self, app):
        self.app = app
        self.db = app.db
        self.running = False
        
    def stop(self):
        """Stop the worker gracefully"""
        logger.info("=================================")
        logger.info("🛑 Stopping background worker...")
        logger.info("=================================")        
        self.running = False
        
    def process_batch(self):
        """
        Process a batch of pending articles.
        Returns number of articles processed.
        """
        from app.coordinator import get_coordinator
        
        coordinator = get_coordinator()
        
        # Only process if coordinator allows
        if not coordinator.can_process():
            return 0
        
        # Find pending articles that haven't exceeded retry limit
        # pending_articles = list(self.db.articles.find({
        pending_articles = list(self.db.news_dataset.find({
            "status": {"$in": ["pending", "failed"]},
            "retry_count": {"$lt": MAX_RETRIES}
        }).sort("created_at", 1).limit(BATCH_SIZE))
        
        if not pending_articles:
            # No more pending - transition to IDLE
            coordinator.set_state(coordinator.IDLE)
            return 0
        
        # Update coordinator with current pending count
        coordinator.update_pending_count(len(pending_articles))
        
        logger.info("===============================================")
        logger.info(f"Processing {len(pending_articles)} articles")
        logger.info("===============================================")
        processed_count = 0
        
        for article in pending_articles:
            article_id = str(article["_id"])
            
            try:
                # Atomically claim this article
                # result = self.db.articles.update_one(
                result = self.db.news_dataset.update_one(
                    {"_id": article["_id"], "status": {"$ne": "processing"}},
                    {"$set": {"status": "processing", "updated_at": datetime.utcnow()}}
                )
                
                if result.modified_count == 0:
                    # Another worker claimed it
                    continue
                
                logger.info(f"📰 [{article_id}] Processing...")
                
                # Get article text (deep scrape if RSS summary is too short)
                raw_text = article.get("raw_text", "")
                original_url = article.get("original_url", "")
                
                # Only scrape if:
                # 1. Content is missing or too short
                # 2. URL is a valid web URL (not internal archive like "BBC_Hindi_Archive_...")
                if len(raw_text) < 200 and original_url.startswith("http"):
                    extraction, _ = extract_article_package(original_url)
                    if extraction.get("success") and extraction.get("content"):
                        raw_text = extraction["content"]
                        # Update raw_text in database
                        # self.db.articles.update_one(
                        self.db.news_dataset.update_one(
                            {"_id": article["_id"]},
                            {"$set": {"raw_text": raw_text}}
                        )
                        
                
                if not raw_text or len(raw_text) < 100:
                    raise ValueError("Article content too short or empty")
                
                # Run PARTIAL pipeline - keywords, entities, event only
                result = process_document_pipeline(
                    db=self.db,
                    doc_id=article_id,
                    raw_text=raw_text,
                    stages=["preprocessing", "translation", "keywords", "entities", "event"],
                    # collection="articles"
                    collection="news_dataset"
                )
                
                if not result.get("success"):
                    raise Exception(result.get("error", "Pipeline failed"))
                
                # Generate embedding for vector search (REFACTORED to use Centralized Model)
                try:
                    from app.services.intelli_search.vector_retriever import get_model
                    
                    # Use the shared singleton model (Supports FP16 automatically)
                    embedding_model = get_model()
                    
                    # Get article text for embedding
                    # article_doc = self.db.articles.find_one({"_id": article["_id"]})
                    article_doc = self.db.news_dataset.find_one({"_id": article["_id"]})
                    title = article_doc.get("translated_title") or article_doc.get("title", "")
                    summary = article_doc.get("translated_summary") or article_doc.get("summary", "")
                    text_to_embed = f"{title} {summary}".strip()
                    
                    if text_to_embed:
                        # Generate embedding
                        embedding = embedding_model.encode(text_to_embed, normalize_embeddings=True)
                        
                        # Store embedding in MongoDB
                        # self.db.articles.update_one(
                        self.db.news_dataset.update_one(
                            {"_id": article["_id"]},
                            {"$set": {"embedding": embedding.tolist()}}
                        )
                        logger.info(f"✅ [{article_id}] Embedding generated (vector search enabled)")
                    
                except Exception as embed_error:
                    # Don't fail the entire process if embedding fails
                    logger.warning(f"[{article_id}] Embedding generation failed: {str(embed_error)}")
                
                # Mark as partial (searchable but not fully analyzed)
                self.db.news_dataset.update_one(
                    {"_id": article["_id"]},
                    {"$set": {
                        "status": "partial",
                        "processed_at": datetime.utcnow(),
                        "retry_count": 0  # Reset on success
                    }}
                )
                
                logger.info("===============================================")
                logger.info(f"✅ [{article_id}] Partial processing complete")
                logger.info("===============================================")
                processed_count += 1
                
                # Notify coordinator
                coordinator.mark_article_processed()
                
            except Exception as e:
                logger.info("===============================================")
                logger.error(f"[{article_id}] ✗ Processing failed: {str(e)}")
                logger.info("===============================================")
                
                # Increment retry counter
                retry_count = article.get("retry_count", 0) + 1
                
                if retry_count >= MAX_RETRIES:
                    logger.error(f"[{article_id}] Max retries exceeded or hard failure, marking as HARD_FAILED")
                    self.db.news_dataset.update_one(
                        {"_id": article["_id"]},
                        {"$set": {"status": "hard_failed", "last_error": str(e), "updated_at": datetime.utcnow()}}
                    )
                else:
                    logger.warning(f"[{article_id}] Processing failed, will retry ({retry_count}/{MAX_RETRIES})")
                    self.db.news_dataset.update_one(
                        {"_id": article["_id"]},
                        {
                            "$set": {
                                "status": "pending",
                                "last_error": str(e),
                                "updated_at": datetime.utcnow()
                            },
                            "$inc": {"retry_count": 1}
                        }
                    )
        
        return processed_count
    
    def run(self):
        """
        Main worker loop - runs continuously.
        """
        logger.info("=================================")
        logger.info("🚀 Background NLP Worker started")
        logger.info(f"Configuration: batch_size={BATCH_SIZE}, sleep={SLEEP_INTERVAL}s")
        logger.info("=================================")
        
        self.running = True
        
        while self.running:
            try:
                with self.app.app_context():
                    processed = self.process_batch()
                
            except Exception as e:
                logger.exception(f"Worker error: {e}")
            
            # Sleep before next batch
            time.sleep(SLEEP_INTERVAL)
        
        logger.info("=================================")
        logger.info("✅ Background worker stopped")
        logger.info("=================================")


if __name__ == "__main__":
    # Create Flask app context
    app = create_app()
    
    # Create and start worker
    worker = BackgroundNLPWorker(app)
    
    try:
        worker.run()
    except KeyboardInterrupt:
        logger.info("=================================")
        logger.info("Worker stopped by user")
        logger.info("=================================")
    except Exception as e:
        logger.info("=================================")
        logger.exception(f"Worker crashed: {e}")
        logger.info("=================================")

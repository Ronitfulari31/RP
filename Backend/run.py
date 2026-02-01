import os
import sys
import time
import logging
import signal
import threading
from threading import Thread
from dotenv import load_dotenv
from app import create_app
from app.database import init_db, close_db
from app.services.scheduler.rss_scheduler import RSSScheduler
# Blueprints will be imported inside main to speed up the prompt

# Environment configuration
os.environ.setdefault(
    "HF_HOME",
    r"D:\Projects\Backend(SA)_cache\hf_cache"
)
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault(
    "ARGOS_PACKAGES_DIR",
    r"D:\Projects\Backend(SA)_cache\argos_cache"
)

# System-wide Temp redirection
TEMP_REDIRECT = r"D:\Projects\Backend(SA)_cache\temp"
os.makedirs(TEMP_REDIRECT, exist_ok=True)
os.environ.setdefault("TEMP", TEMP_REDIRECT)
os.environ.setdefault("TMP", TEMP_REDIRECT)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = create_app()
# Blueprints will be registered inside main


@app.route("/api/nlp-features", methods=["GET"])
def get_nlp_features():
    return {
        "status": "success",
        "features": [
            "Sentiment Analysis (BERTweet / VADER / TextBlob)",
            "Multilingual Translation",
            "Event Detection (Keyword + ML Hybrid)",
            "Location Extraction (NER)",
            "Cross-Lingual Evaluation",
        ],
    }, 200
@app.errorhandler(404)
def not_found(error):
    return {
        "status": "error",
        "message": "Resource not found",
        "path": str(error),
    }, 404
@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal Server Error: {error}")
    return {
        "status": "error",
        "message": "Internal server error",
    }, 500

# Global worker instance
background_worker = None
worker_thread = None

def start_background_worker():
    """Start the background NLP worker in a separate thread"""
    global background_worker, worker_thread
    
    if background_worker is not None and background_worker.running:
        logger.warning("Background worker is already running")
        return
    
    logger.info("🚀 Starting background NLP worker...")
    from backgroundNLPworker import BackgroundNLPWorker
    background_worker = BackgroundNLPWorker(app)
    
    # Run worker in daemon thread (stops when main process stops)
    worker_thread = threading.Thread(target=background_worker.run, daemon=True)
    worker_thread.start()
    
    # Attach to app for API access
    app.background_worker = background_worker
    logger.info("✅ Background worker started successfully")

def handle_shutdown(*args):
    logger.info("🛑 Shutdown signal received")
    if background_worker:
        logger.info("Stopping background NLP worker...")
        background_worker.stop()
        if worker_thread and worker_thread.is_alive():
            worker_thread.join(timeout=5) # Give worker a chance to finish
            if worker_thread.is_alive():
                logger.warning("Background worker did not stop gracefully.")
    logger.info("👋 Server stopped cleanly")
    logger.info("===================================================")
    os._exit(0)

signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)

if __name__ == "__main__":
    # ---------------------------------------------------------
    # EARLY CHECKPOINT (Main Thread)
    # ---------------------------------------------------------
    # Pause background work as per user request (have dataset already)
    start_paused = True

    # ---------------------------------------------------------
    # DEFERRED BLUEPRINT REGISTRATION
    # ---------------------------------------------------------
    from app.routes.auth import auth_bp
    from app.routes.documents import documents_bp
    from app.routes.reports import reports_bp
    from app.routes.settings import settings_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.news import news_bp
    from app.routes.translation_api import translation_bp
    from app.routes.coordinator import coordinator_bp
    from app.routes.intelli_search import intelli_search_bp
    from app.routes.evaluation import evaluation_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(documents_bp, url_prefix="/api/documents")
    app.register_blueprint(reports_bp, url_prefix="/api")
    app.register_blueprint(settings_bp, url_prefix="/api")
    app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
    app.register_blueprint(news_bp, url_prefix="/api/news")
    app.register_blueprint(translation_bp, url_prefix="/api/translation")
    app.register_blueprint(coordinator_bp)
    app.register_blueprint(intelli_search_bp, url_prefix="/api/intelli-search")
    app.register_blueprint(evaluation_bp, url_prefix="/api/evaluations")

    # ---------------------------------------------------------
    # DEFERRED MODEL WARMUP (Background Thread)
    # ---------------------------------------------------------
    def warmup_models():
        try:
            import torch
            import time
            time.sleep(1) # Reduced from 5s
            
            # Step 1: Preprocessing (LID)
            try:
                from app.services.core.preprocessing import preprocessing_service
                preprocessing_service.warmup()
            except Exception as e: logger.error(f"LID Warmup Failed: {e}")
            
            # Step 2: NER (GLiNER)
            try:
                from app.services.analysis.ner_service import ner_service
                ner_service.warmup()
            except Exception as e: logger.error(f"NER Warmup Failed: {e}")
            
            # Step 3: Translation (NLLB)
            try:
                from app.services.analysis.translation_service import translation_service
                translation_service.warmup()
            except Exception as e: logger.error(f"Translation Warmup Failed: {e}")
            
            # Step 4: Summarization (BART)
            try:
                from app.services.analysis.summarization import summarization_service
                summarization_service.warmup()
            except Exception as e: logger.error(f"Summarization Warmup Failed: {e}")
            
            # Step 5: Category Classification (BART-Large)
            try:
                from app.services.analysis.classification.category_classifier import warmup as cat_warmup
                cat_warmup()
            except Exception as e: logger.error(f"Category Warmup Failed: {e}")
            
            # Step 6: Sentiment (RoBERTa)
            try:
                from app.services.analysis.sentiment_service import get_sentiment_service
                get_sentiment_service().warmup()
            except Exception as e: logger.error(f"Sentiment Warmup Failed: {e}")
            
            # Step 7: Embedding (Multilingual E5)
            try:
                from app.services.intelli_search.vector_retriever import get_model
                get_model() # Forces load
                logger.info("✅ [Background] Embedding Model Warmup Complete")
            except Exception as e: logger.error(f"Embedding Warmup Failed: {e}")

            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            logger.info("DONE: ALL AI MODELS WARMED UP AND READY FOR INSTANT INFERENCE")
        except Exception as e:
            logger.error(f"ERR: [Background] Multi-Model Warmup Critical Failure: {e}")

    # Start warmup in background so API stands up immediately
    threading.Thread(target=warmup_models, daemon=True).start()

    # ---------------------------------------------------------
    # START BACKGROUND SCHEDULER
    # ---------------------------------------------------------
    scheduler = RSSScheduler(interval_minutes=1)
    app.scheduler = scheduler
    if start_paused:
        scheduler.pause()
    
    Thread(target=scheduler.start, daemon=True).start()
    
    # ---------------------------------------------------------
    # START BACKGROUND NLP WORKER (Async)
    # ---------------------------------------------------------
    def deferred_worker_start():
        logger.info("🚀 Loading NLP models in background...")
        from backgroundNLPworker import BackgroundNLPWorker
        worker = BackgroundNLPWorker(app)
        app.background_worker = worker
        worker.run()

    # Thread(target=deferred_worker_start, daemon=True).start()
    logger.info("⏸️ Background worker disabled by user request")

    app.run(
        debug=os.getenv("FLASK_DEBUG", True),
        host=os.getenv("FLASK_HOST", "0.0.0.0"),
        port=int(os.getenv("FLASK_PORT", 5000)),
        use_reloader=False  # Windows-safe, avoids duplicate ML loads
    )

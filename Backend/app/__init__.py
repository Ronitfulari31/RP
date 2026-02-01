import logging
import os
import warnings

# ---------------------------------------------------------
# Environment Safeguards (Early Initialization)
# ---------------------------------------------------------
from dotenv import load_dotenv
load_dotenv()

CACHE_BASE_PATH = os.getenv("CACHE_BASE_PATH", r"D:\Projects\Backend(SA)_cache")
os.environ["ARGOS_PACKAGES_DIR"] = os.path.join(CACHE_BASE_PATH, "argos_cache", "packages")
os.environ["TEMP"] = os.path.join(CACHE_BASE_PATH, "temp")
os.environ["TMP"] = os.environ["TEMP"]
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
warnings.filterwarnings("ignore", category=FutureWarning, module="transformers.utils.hub")

import sys
from datetime import timedelta

# Silence verbose third-party loggers
logging.getLogger('argostranslate').setLevel(logging.CRITICAL)
logging.getLogger('argostranslate.utils').setLevel(logging.CRITICAL)
logging.getLogger('argostranslate.translate').setLevel(logging.CRITICAL)
logging.getLogger('stanza').setLevel(logging.CRITICAL)
logging.getLogger('werkzeug').setLevel(logging.WARNING)

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from app.config import config
from app.middleware.error_handler import register_error_handlers


# ---------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("argostranslate").setLevel(logging.ERROR)
logging.getLogger("argostranslate.utils").setLevel(logging.ERROR)
logging.getLogger("app.services.discovery.fetch.rss_fetcher").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

socketio = None  # Placeholder


# ---------------------------------------------------------
# Application Factory
# ---------------------------------------------------------
def create_app(config_name='development'):
    """Application factory"""
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(config[config_name])

    # -----------------------------------------------------
    # Initialize Extensions
    # -----------------------------------------------------
    cors_origins = app.config.get('CORS_ORIGINS', '*')
    CORS(app, resources={r"/api/*": {"origins": cors_origins}}, supports_credentials=True)
    JWTManager(app)

    # -----------------------------------------------------
    # Database Initialization
    # -----------------------------------------------------
    from app.database import init_db
    init_db(app)

    # -----------------------------------------------------
    # Register Error Handlers
    # -----------------------------------------------------
    register_error_handlers(app)

    # translation_service.init_argos() is now lazy-loaded on first use



    return app

from pymongo import MongoClient
import logging

logger = logging.getLogger(__name__)

db = None
client = None


def init_db(app):
    """
    Initialize MongoDB connection and attach it to the Flask app.
    Ensures the connection is verified and accessible globally.
    """
    global db, client
    try:
        # Load URI from Flask config or fallback to default local DB (without db name)
        mongodb_uri = app.config.get(
            'MONGODB_URI',
            'mongodb://localhost:27017/'  # Removed db name from default
        )

        # Establish connection with timeout
        client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')  # Test connection

        # Explicitly select database from config
        db_name = app.config["MONGODB_DB_NAME"]
        db = client[db_name]
        app.db = db
        app.mongo_client = client
        
        logger.info("===================================================")
        logger.info(f"✓ Connected to MongoDB: {mongodb_uri}")
        logger.info(f"✓ Using database: {db_name}")
        logger.info("===================================================")

        collections = db.list_collection_names()
        if collections:
            logger.info("===================================================")
            logger.info(f"✓ Available collections: {collections}")
            logger.info("===================================================")
        else:
            logger.info("ℹ No collections found yet — database initialized empty.")
        logger.info("===================================================")

        return db

    except Exception as e:
        logger.info("===================================================")
        logger.error(f"✗ Failed to connect to MongoDB: {str(e)}")
        logger.warning("⚠ Proceeding without MongoDB connection — some features may not work.")
        logger.info("===================================================")
        app.db = None
        app.mongo_client = None
        return None
        logger.info("===================================================")


def get_db():
    """
    Get the active MongoDB connection.
    Logs a warning if accessed before initialization.
    """
    global db
    logger.info("===================================================")
    if db is None:
        logger.warning("⚠ Database not initialized. Call init_db(app) first.")
    return db
    logger.info("===================================================")


def close_db():
    """
    Gracefully close MongoDB connection.
    Useful for shutdowns or tests.
    """
    global client
    if client:
        logger.info("===================================================")
        client.close()
        logger.info("✓ MongoDB connection closed.")
        logger.info("===================================================")

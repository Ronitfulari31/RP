# Article Store - Persistence Layer
import logging
from datetime import datetime, timedelta
from app.database import get_db
from app.models.article import Article


class ArticleStore:
    # def __init__(self, collection_name="articles"):
    def __init__(self, collection_name="news_dataset"):
        self._collection = None
        self.collection_name = collection_name

    @property
    def collection(self):
        if self._collection is None:
            from app.database import get_db
            db = get_db()
            if db is None:
                raise RuntimeError("Database not initialized. Call init_db(app) first.")
            self._collection = db[self.collection_name]
            
            # Ensure unique index on URL
            try:
                self._collection.create_index(
                    "original_url",
                    unique=True,
                    background=True
                )
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.warning(f"⚠️ Could not create unique index on original_url: {e}")

            # ⚙️ Lifecycle Indices (Optimization for filtering by status/analyzed)
            self._collection.create_index([("status", 1)], background=True)
            self._collection.create_index([("analyzed", 1)], background=True)
            self._collection.create_index([("status", 1), ("created_at", -1)], background=True)

            # TTL index (Commented out for now to retain more articles)
            # self._collection.create_index(
            #     "created_at",
            #     expireAfterSeconds=259200 # 72 hours (3 days)
            # )

            # 🔍 Global Text Search Index
            logger = logging.getLogger(__name__)
            try:
                self._collection.create_index(
                    [
                        ("keywords", "text"),
                        ("translated_title", "text"),
                        ("title", "text"),
                        ("translated_summary", "text"),
                        ("summary", "text")
                    ],
                    name="ArticleTextIndex",
                    weights={
                        "keywords": 15,
                        "translated_title": 10,
                        "title": 10,
                        "translated_summary": 5,
                        "summary": 5
                    },
                    background=True,
                    default_language="none",
                    language_override="none"
                )
                logger.info("MongoDB Text Search Index ensured.")
            except Exception as e:
                logger.warning(f"Text index creation skipped or failed: {e}")
            
            # 🚀 Automatic View Creation
            self._ensure_views(db)
            
        return self._collection

    def _ensure_views(self, db):
        """Create Virtual Collections (Views) for better organization in DB viewers"""
        logger = logging.getLogger(__name__)
        view_configs = {
            "view_pending_news": [{"$match": {"status": "pending"}}],
            "view_partial_news": [{"$match": {"status": "partial"}}],
            "view_analyzed_news": [{"$match": {"status": "fully_analyzed"}}]
        }
        
        existing_collections = db.list_collection_names()
        
        for view_name, pipeline in view_configs.items():
            if view_name not in existing_collections:
                try:
                    db.create_collection(
                        view_name,
                        viewOn=self.collection_name,
                        pipeline=pipeline
                    )
                    logger.info(f"Created virtual view: {view_name}")
                except Exception as e:
                    logger.warning(f"Could not create view {view_name}: {e}")

    def save_if_new(self, article: Article):
        """
        Insert article if URL not already present.
        Returns stored document or None if duplicate.
        """
        try:
            result = self.collection.insert_one(article.to_dict())
            return self.collection.find_one({"_id": result.inserted_id})
        except Exception:
            # Duplicate URL
            return None

    def fetch_recent(self, context, limit=50):
        """
        Fetch recent articles matching context.
        """
        # Normalize to lowercase for case-insensitive matching
        query = {
            "language": {"$in": context["language"]},
            "continent": str(context["continent"]).lower()
        }

        if context["country"] != "unknown":
            query["country"] = str(context["country"]).lower()

        return list(
            self.collection
            .find(query)
            .sort("created_at", -1)
            .limit(limit)
        )

    def fetch_recent_by_context(self, context, minutes=30, limit=50):
        """
        Cache-first fetch:
        Return recent articles matching context if within freshness window.
        """
        since = datetime.utcnow() - timedelta(minutes=minutes)

        # Normalize to lowercase for case-insensitive matching
        query = {
            "created_at": {"$gte": since},
            "language": {"$in": context["language"]},
            "continent": str(context["continent"]).lower()
        }

        if context["country"] != "unknown":
            query["country"] = str(context["country"]).lower()

        if context["category"] != "unknown":
            query["category"] = str(context["category"]).lower()

        return list(
            self.collection
            .find(query)
            .sort("created_at", -1)
            .limit(limit)
        )

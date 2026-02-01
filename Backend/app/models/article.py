
# Article Model
from datetime import datetime
from bson import ObjectId


class Article:
    inferred_category: str = "unknown"
    category_confidence: float = 0.0
    inferred_categories: list = []

    def __init__(
        self,
        title,
        original_url,
        source,
        published_date=None,
        summary="",
        language=None,
        country=None,
        continent=None,
        category=None,
        image_url=None,
        inferred_category="unknown",
        category_confidence=0.0,
        inferred_categories=None,
        status="pending",  # Added for two-phase processing
        retry_count=0,  # Added for two-phase processing
        last_error=None,  # Added for two-phase processing
        processed_at=None,  # Added for two-phase processing
        translated_title=None,
        translated_summary=None,
        keywords=None,
    ):
        self._id = ObjectId()
        self.title = title
        self.original_url = original_url
        self.source = source
        self.published_date = published_date
        self.summary = summary
        self.image_url = image_url

        self.language = language
        self.country = country
        self.continent = continent
        self.category = category
        self.inferred_category = inferred_category
        self.category_confidence = category_confidence
        self.inferred_categories = inferred_categories or []

        self.created_at = datetime.utcnow()
        self.analyzed = False
        self.status = status  # Added for two-phase processing
        self.retry_count = retry_count  # Added for two-phase processing
        self.last_error = last_error  # Added for two-phase processing
        self.processed_at = processed_at  # Added for two-phase processing
        
        # New Search-Optimized Fields
        self.translated_title = translated_title
        self.translated_summary = translated_summary
        self.keywords = keywords or []

    def to_dict(self):
        return {
            "_id": self._id,
            "title": self.title,
            "original_url": self.original_url,
            "source": self.source,
            "published_date": self.published_date,
            "summary": self.summary,
            "language": self.language,
            "country": self.country,
            "continent": self.continent,
            "category": self.category,
            "image_url": self.image_url,
            "inferred_category": self.inferred_category,
            "category_confidence": self.category_confidence,
            "inferred_categories": self.inferred_categories,
            "created_at": self.created_at,
            "analyzed": self.analyzed,
            # Two-phase processing fields
            "status": self.status,
            "retry_count": self.retry_count,
            "last_error": self.last_error,
            "processed_at": self.processed_at,
            "translated_title": self.translated_title,
            "translated_summary": self.translated_summary,
            "keywords": self.keywords,
        }


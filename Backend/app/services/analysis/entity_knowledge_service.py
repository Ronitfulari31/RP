"""
Entity Knowledge Service
-------------------------
Automatically learns entities from processed documents and builds a knowledge base
that grows over time. Entities are stored in MongoDB and reused for future translations.
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional
from bson import ObjectId
from bson.errors import InvalidId

logger = logging.getLogger(__name__)


class EntityKnowledgeService:
    """
    Manages the automatic entity learning system.
    Stores detected entities in MongoDB and retrieves them for future use.
    """

    def __init__(self, db=None):
        """
        Initialize the service with database connection.
        
        Args:
            db: MongoDB database instance
        """
        self.db = db
        self._cache = {}
        self._cache_timestamp = None
        self._cache_ttl = 300  # Cache for 5 minutes
        self._initialized = db is not None
        
        if db is not None:
            self._ensure_indexes()

    def set_db(self, db):
        """
        Initialize or set the database connection (idempotent).
        Safe to call multiple times.
        
        Args:
            db: MongoDB database instance
        """
        if db is not None and not self._initialized:
            self.db = db
            self._initialized = True
            self._ensure_indexes()
        elif db is not None and self._initialized:
            # Already initialized, no-op (safe idempotent call)
            pass

    def _ensure_indexes(self):
        """Create indexes for optimal query performance"""
        try:
            # Unique index on entity text
            self.db.entity_knowledge.create_index("text", unique=True)
            
            # Index for finding common entities
            self.db.entity_knowledge.create_index([("occurrences", -1)])
            
            # Index for finding recent entities
            self.db.entity_knowledge.create_index([("last_seen", -1)])
            
            # Index for filtering by label
            self.db.entity_knowledge.create_index("label")
            
            logger.info("Entity knowledge indexes created successfully")
        except Exception as e:
            logger.warning(f"Failed to create indexes: {e}")

    def learn_entity(
        self,
        entity_text: str,
        canonical_en: str,
        label: str,
        confidence: float,
        context: str,
        doc_id: str
    ) -> bool:
        """
        Learn a new entity or update an existing one.
        
        Args:
            entity_text: Original entity text (e.g., "रामलला")
            canonical_en: English translation (e.g., "Ram Lalla")
            label: Entity type (e.g., "DEITY")
            confidence: Detection confidence (0.0-1.0)
            context: Text context where entity appeared
            doc_id: Source document ID
            
        Returns:
            True if successful, False otherwise
        """
        if self.db is None:
            logger.warning("No database connection - cannot learn entity")
            return False

        try:
            # Check if entity already exists
            existing = self.db.entity_knowledge.find_one({"text": entity_text})
            
            # Convert doc_id to ObjectId if possible, otherwise keep as string
            try:
                doc_object_id = ObjectId(doc_id)
            except InvalidId:
                doc_object_id = doc_id  # Keep as string if conversion fails
            
            if existing:
                # Update existing entity
                self.db.entity_knowledge.update_one(
                    {"text": entity_text},
                    {
                        "$set": {
                            "last_seen": datetime.utcnow(),
                            "canonical_en": canonical_en,  # Update translation
                            "label": label,  # Update label if changed
                            # Update confidence as weighted average
                            "confidence": (
                                existing["confidence"] * existing["occurrences"] + confidence
                            ) / (existing["occurrences"] + 1)
                        },
                        "$inc": {
                            "occurrences": 1
                        },
                        "$addToSet": {
                            "contexts": {"$each": [context]},
                            "source_documents": doc_object_id
                        }
                    }
                )
                logger.info(f"Updated entity: {entity_text} (now seen {existing['occurrences'] + 1} times)")
            else:
                # Insert new entity
                self.db.entity_knowledge.insert_one({
                    "text": entity_text,
                    "canonical_en": canonical_en,
                    "label": label,
                    "confidence": confidence,
                    "occurrences": 1,
                    "first_seen": datetime.utcnow(),
                    "last_seen": datetime.utcnow(),
                    "contexts": [context],
                    "source_documents": [doc_object_id]
                })
                logger.info(f"Learned new entity: {entity_text} → {canonical_en} ({label})")
            
            # Invalidate cache
            self._cache = {}
            self._cache_timestamp = None
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to learn entity {entity_text}: {e}")
            return False

    def get_learned_entities(self, text: str) -> List[Dict]:
        """
        Get all learned entities that appear in the given text.
        Uses whole-word matching to avoid partial word matches.
        
        Args:
            text: Text to search for entities
            
        Returns:
            List of entity dictionaries with text, canonical_en, label, etc.
        """
        if self.db is None:
            return []

        try:
            import re
            
            # Extract candidate terms from text to optimize DB query
            candidate_terms = self._extract_candidate_terms(text)
            
            if not candidate_terms:
                return []
            
            # Query DB for entities that match candidate terms
            entities_from_db = list(self.db.entity_knowledge.find({
                "text": {"$in": candidate_terms}
            }))
            
            # Filter entities that appear in the text as whole words (additional validation)
            found_entities = []
            for entity in entities_from_db:
                entity_text = entity.get("text", "")
                if not entity_text:
                    continue
                
                # Use word boundary matching instead of substring search
                pattern = r'(?:^|\s|[^\w\u0900-\u097F\u4e00-\u9fff])' + re.escape(entity_text) + r'(?:$|\s|[^\w\u0900-\u097F\u4e00-\u9fff])'
                if re.search(pattern, text, re.UNICODE):
                    found_entities.append({
                        "text": entity_text,
                        "canonical_en": entity["canonical_en"],
                        "label": entity["label"],
                        "confidence": entity["confidence"],
                        "gloss_en": entity["canonical_en"],  # Alias for compatibility
                        "learned": True,  # Mark as learned entity
                        "occurrences": entity["occurrences"]
                    })
            
            if found_entities:
                logger.info(f"Found {len(found_entities)} learned entities in text")
            
            return found_entities
            
        except Exception as e:
            logger.error(f"Failed to get learned entities: {e}")
            return []
    
    def _extract_candidate_terms(self, text: str) -> List[str]:
        """
        Extract candidate terms from text that might match known entities.
        Splits text on whitespace and special characters to get candidate phrases.
        
        Args:
            text: Text to extract candidates from
            
        Returns:
            List of candidate terms to search for in the knowledge base
        """
        import re
        # Split on whitespace and common delimiters, keeping some phrases
        candidates = set()
        
        # Single word terms (space-separated)
        words = text.split()
        candidates.update(words)
        
        # Also try 2-3 word combinations for entity phrases
        for i in range(len(words) - 1):
            candidates.add(" ".join(words[i:i+2]))
            if i < len(words) - 2:
                candidates.add(" ".join(words[i:i+3]))
        
        # Remove very short terms and empty strings
        candidates = {t.strip() for t in candidates if t.strip() and len(t.strip()) >= 2}
        
        return list(candidates)

    def get_all_entities(self, min_occurrences: int = 1) -> List[Dict]:
        """
        Get all entities from the knowledge base.
        
        Args:
            min_occurrences: Minimum number of occurrences to include
            
        Returns:
            List of all learned entities
        """
        if self.db is None:
            return []

        try:
            entities = list(self.db.entity_knowledge.find(
                {"occurrences": {"$gte": min_occurrences}}
            ).sort("occurrences", -1))
            
            return entities
            
        except Exception as e:
            logger.error(f"Failed to get all entities: {e}")
            return []

    def get_entity_stats(self) -> Dict:
        """
        Get statistics about the entity knowledge base.
        
        Returns:
            Dictionary with stats (total_entities, by_label, etc.)
        """
        if self.db is None:
            return {}

        try:
            total = self.db.entity_knowledge.count_documents({})
            
            # Count by label
            pipeline = [
                {"$group": {
                    "_id": "$label",
                    "count": {"$sum": 1}
                }}
            ]
            by_label = {item["_id"]: item["count"] for item in self.db.entity_knowledge.aggregate(pipeline)}
            
            # Most common entities
            top_entities = list(self.db.entity_knowledge.find().sort("occurrences", -1).limit(10))
            
            return {
                "total_entities": total,
                "by_label": by_label,
                "top_entities": [
                    {
                        "text": e["text"],
                        "canonical_en": e["canonical_en"],
                        "occurrences": e["occurrences"]
                    }
                    for e in top_entities
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to get entity stats: {e}")
            return {}


# Singleton instance (will be initialized with db in app startup)
entity_knowledge_service = EntityKnowledgeService()

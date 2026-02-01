# app/models/document.py
"""
Document Model - Updated for Category-Based News & Multimodal Analysis
Supports: categories, subcategories, multilingual pipeline, AI analysis
"""

from datetime import datetime
from bson import ObjectId
from typing import Optional, Dict, List


class Document:
    """Document model with multilingual pipeline & category support"""

    @staticmethod
    def create(
        db,
        user_id: str,
        raw_text: str,
        filename: Optional[str] = None,
        file_path: Optional[str] = None,
        file_type: Optional[str] = None,
        source: str = 'file',
        location_hint: Optional[str] = None,
        event_type_hint: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """
        Create a new document record.
        Supports dynamic categories & future extensions.
        """

        # ---------------- DEFAULT METADATA (SAFE BASE) ----------------
        base_metadata = {
            # News identity
            'title': None,
            'original_url': None,
            'resolved_url': None,
            'publisher': None,
            'published_date': None,
            'image_url': None,

            # CATEGORY SYSTEM (KEY CHANGE)
            'category': None,        # sports, business, etc.
            'sub_category': None,    # cricket, football, flood, etc.

            # Content typing
            'content_type': None,    # headline | full_article
            'source_type': None,     # newsapi | scraper | file

            # Lifecycle
            'status': 'pending_analysis'
        }

        # Merge provided metadata (overrides defaults)
        final_metadata = {**base_metadata, **(metadata or {})}

        doc = {
            # ---------------- Raw content ----------------
            'raw_text': raw_text,
            'clean_text': None,

            # ---------------- Language ----------------
            'language': None,
            'text_hash': None,

            # ---------------- Translation ----------------
            'translated_text': None,
            'translated_to_en': False,
            'translation_engine': None,
            'translation_time': None,

            # ---------------- Source ----------------
            'source': source,           # file | news | social
            'user_id': user_id,
            'timestamp': datetime.utcnow(),

            'location_hint': location_hint,
            'event_type_hint': event_type_hint,

            # ---------------- File info ----------------
            'filename': filename,
            'file_path': file_path,
            'file_type': file_type,

            # ---------------- Analysis ----------------
            'sentiment': {
                'label': 'pending',
                'confidence': 0.0,
                'method': 'uninitialized',
                'scores': {}
            },

            'event_type': None,
            'event_confidence': None,
            'locations': [],

            # ---------------- Performance ----------------
            'processing_time': None,
            'pipeline_metrics': {
                'preprocessing_time': None,
                'translation_time': None,
                'sentiment_time': None,
                'event_detection_time': None,
                'ner_time': None
            },

            # ---------------- Metadata ----------------
            'metadata': final_metadata,

            # ---------------- System ----------------
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'processed': False
        }

        result = db.documents.insert_one(doc)
        return str(result.inserted_id)

    # ---------------- UPDATE METHODS (UNCHANGED) ----------------

    @staticmethod
    def update_preprocessing(db, doc_id, clean_text, language, text_hash, preprocessing_time, collection="documents"):
        db[collection].update_one(
            {'_id': ObjectId(doc_id)},
            {'$set': {
                'clean_text': clean_text,
                'language': language,
                'text_hash': text_hash,
                'pipeline_metrics.preprocessing_time': preprocessing_time,
                'updated_at': datetime.utcnow()
            }}
        )

    @staticmethod
    def update_translation(db, doc_id, translated_text, engine, time_taken, collection="documents"):
        db[collection].update_one(
            {'_id': ObjectId(doc_id)},
            {'$set': {
                'translated_text': translated_text,
                'translated_to_en': True,
                'translation_engine': engine,
                'translation_time': time_taken,
                'pipeline_metrics.translation_time': time_taken,
                'updated_at': datetime.utcnow()
            }}
        )

    @staticmethod
    def update_sentiment(db, doc_id, label=None, confidence=0.0, method="unknown", scores=None, time_taken=0.0, sentiment=None, collection="documents"):
        # Handle cases where 'sentiment' is used instead of 'label'
        final_label = label if label is not None else sentiment
        if final_label is None:
            final_label = "neutral"
            
        db[collection].update_one(
            {'_id': ObjectId(doc_id)},
            {'$set': {
                'sentiment.label': final_label,
                'sentiment.confidence': confidence,
                'sentiment.method': method,
                'sentiment.scores': scores or {},
                'pipeline_metrics.sentiment_time': time_taken,
                'updated_at': datetime.utcnow()
            }}
        )

    @staticmethod
    def update_event(db, doc_id, event_type, confidence, time_taken, collection="documents"):
        db[collection].update_one(
            {'_id': ObjectId(doc_id)},
            {'$set': {
                'event_type': event_type,
                'event_confidence': confidence,
                'pipeline_metrics.event_detection_time': time_taken,
                'updated_at': datetime.utcnow()
            }}
        )

    @staticmethod
    def update_locations(db, doc_id, locations, time_taken, collection="documents"):
        db[collection].update_one(
            {'_id': ObjectId(doc_id)},
            {'$set': {
                'locations': locations,
                'pipeline_metrics.ner_time': time_taken,
                'updated_at': datetime.utcnow()
            }}
        )

    @staticmethod
    def mark_processed(db, doc_id, processing_time, collection="documents"):
        db[collection].update_one(
            {'_id': ObjectId(doc_id)},
            {'$set': {
                'processed': True,
                'processing_time': processing_time,
                'updated_at': datetime.utcnow()
            }}
        )

    @staticmethod
    def update_from_dag_context(db, doc_id, context, collection="documents"):
        """Compulsively syncs DAG context back to MongoDB."""
        update_payload = {
            "summary": context.get("summary"),
            "sentiment": context.get("sentiment"),
            "keywords": context.get("keywords"),
            "entities": context.get("entities"),
            "category": context.get("category"),
            "category_confidence": context["scores"].get("category_confidence", 0.0),
            "event_type": context.get("category"),
            "event_confidence": context["scores"].get("category_confidence", 0.0),
            "locations": context.get("locations"),
            "clean_text": context.get("cleaned_text"),
            "language": context.get("language"),
            "translated_text": context.get("translated_text"),
            "translated_to_en": context.get("translated_to_en", False),
            "text_hash": context.get("content_hash"),
            "processed": True,
            "processing_time": sum(context.get("processing_time", {}).values()),
            "pipeline_metrics": {
                "preprocessing_time": context.get("processing_time", {}).get("Preprocessing", 0.0),
                "translation_time": context.get("processing_time", {}).get("Translation", 0.0),
                "sentiment_time": context.get("processing_time", {}).get("SentimentAnalysis", 0.0),
                "event_detection_time": context.get("processing_time", {}).get("CategoryClassification", 0.0),
                "ner_time": context.get("processing_time", {}).get("NER", 0.0)
            },
            "scores": context.get("scores"),
            "flags": context.get("flags"),
            "tier": context.get("tier"),
            "processing_mode": context.get("processing_mode"),
            "processing_path": context.get("processing_path"),
            "failed_gate": context.get("failed_gate"),
            "execution_time_ms": context.get("execution_time_ms"),
            "analyzed": True,
            "metadata.status": "completed",
            "updated_at": datetime.utcnow()
        }
        
        # Add embedding if present
        if context.get("embedding"):
            update_payload["embedding"] = context["embedding"]

        db[collection].update_one(
            {"_id": ObjectId(doc_id)},
            {"$set": update_payload}
        )

    @staticmethod
    def get_by_filters(db, user_id=None, event_type=None, sentiment=None, language=None, source=None, limit=100):
        """Get documents with optional filtering and sorting"""
        query = {}
        
        if user_id:
            query['user_id'] = user_id
            
        if event_type:
            query['event_type'] = event_type
            
        if sentiment:
            query['sentiment.label'] = sentiment
            
        if language:
            query['language'] = language
            
        if source:
            query['source'] = source
        else:
            # Default: Exclude pasted text from main lists
            query['source'] = {'$ne': 'pasted_text'}
            
        # Sort by created_at descending (newest first)
        return list(db.documents.find(query).sort('created_at', -1).limit(limit))

    @staticmethod
    def get_by_id(db, doc_id):
        return db.documents.find_one({'_id': ObjectId(doc_id)})

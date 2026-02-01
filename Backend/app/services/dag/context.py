def create_initial_context(raw_text: str, document_id: str = None, metadata: dict = None, db=None) -> dict:
    """
    Creates a standardized shared context for the DAG pipeline.
    """
    context = {
        "document_id": document_id,
        "raw_text": raw_text,
        "cleaned_text": "",
        "language": "unknown",
        "content_hash": "",

        # Translation
        "translated_text": "",
        "translation_method": "none",
        "translated_to_en": False,

        # NLP outputs
        "entities": [],
        "keywords": [],
        "locations": {
            "city": "Unknown",
            "state": "Unknown",
            "country": "Unknown",
            "confidence": 0.0
        },
        "summary": {},
        "sentiment": {
            "label": "neutral",
            "confidence": 0.0,
            "scores": {}
        },
        "category": "unknown",

        # Embeddings
        "embedding": None,

        # Control & quality
        "scores": {
            "language_confidence": 0.0,
            "text_quality": 0.0,
            "translation_quality": 0.0,
            "nlp_quality": 0.0,
            "category_confidence": 0.0,
            "summary_quality": 0.0,
            "overall": 0.0
        },
        "flags": [],
        "processing_mode": "full",   # full | reduced | embedding_only
        "rejected": False,
        "rejection_reason": None,
        "rejected_at_node": None,
        
        # Metadata & Tiering
        "tier": 3,
        "processing_time": {},
        
        # Database connection for entity learning
        "db": db
    }

    # Inject metadata hints if provided
    if metadata:
        for key, value in metadata.items():
            if value is not None:
                context[key] = value

    return context

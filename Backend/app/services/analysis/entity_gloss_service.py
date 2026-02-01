import re
import logging
from typing import List, Dict
from functools import lru_cache

logger = logging.getLogger(__name__)

class EntityGlossService:
    """
    Adds human-readable English explanations and standardized labels 
    to source entities without altering entity text or translation.
    
    Now supports automatic entity learning from processed documents.
    """

    # Static map with enriched metadata: (gloss, label_override, confidence)
    def __init__(self, db=None):
        self._cache = {}
        self.db = db
        self._learned_entities_cache = {}
        
        # Initialize knowledge service if db provided
        if db is not None:
            from app.services.analysis.entity_knowledge_service import entity_knowledge_service
            entity_knowledge_service.db = db

    def enrich(self, entities: List[Dict]) -> List[Dict]:
        """
        Enriches a list of entities with 'gloss_en', 'gloss_confidence', 
        and standardized labels using the dynamic Knowledge Base.
        """
        if not entities:
            return []

        # If we have no DB, we can't enrich dynamically
        if self.db is None:
            logger.warning("No database connection - dynamic enrichment disabled")
            return entities

        from app.services.analysis.entity_knowledge_service import entity_knowledge_service
        
        enriched = []
        for ent in entities:
            text = ent.get("text", "")
            
            # Lookup in Knowledge Base with error handling
            try:
                existing = self.db.entity_knowledge.find_one({"text": text})
                
                if existing:
                    ent["gloss_en"] = existing["canonical_en"]
                    ent["canonical_en"] = existing["canonical_en"]
                    ent["gloss_confidence"] = existing.get("confidence", 1.0)
                    ent["label"] = existing["label"]
                    ent["source"] = "knowledge_base"
            except Exception as e:
                logger.error(f"Failed to lookup entity '{text}' in knowledge base: {e}")
                # Continue without mutating ent, keep original values
            
            enriched.append(ent)
        
        return enriched
    
    def inject_missing_entities(self, text: str, entities: List[Dict]) -> List[Dict]:
        """
        Inject known entities from the Knowledge Base that NER missed.
        
        Args:
            text: Source text to search
            entities: Existing detected entities
            
        Returns:
            Combined list of detected + injected entities
        """
        if self.db is None:
            return entities

        from app.services.analysis.entity_knowledge_service import entity_knowledge_service
        
        detected_texts = {ent.get("text", "") for ent in entities}
        injected = list(entities)
        
        # Get all entities that appear in the text from Knowledge Base with error handling
        try:
            learned = entity_knowledge_service.get_learned_entities(text)
        except Exception as e:
            logger.error(f"Failed to get learned entities: {e}")
            learned = []  # Safe default on error
        
        for learned_ent in learned:
            ent_text = learned_ent["text"]
            if ent_text not in detected_texts:
                # 🚀 Priority 2: Use word boundary regex instead of simple find
                # Supports Devanagari and Chinese scripts
                # Use capturing group to get exact entity positions
                pattern = r'(?:^|\s|[^\w\u0900-\u097F\u4e00-\u9fff])(' + re.escape(ent_text) + r')(?:$|\s|[^\w\u0900-\u097F\u4e00-\u9fff])'
                match = re.search(pattern, text, re.UNICODE)
                if not match:
                    continue  # skip – not a clean whole-word match

                # Extra safety: skip very common religious terms unless very high confidence
                if learned_ent.get('label') == 'DEITY' and learned_ent.get('confidence', 0) < 0.94:
                    logger.debug(f"Blocked low-confidence deity injection: {ent_text}")
                    continue

                # Only inject if short context looks relevant (very simple version)
                start, end = match.span(1)  # Get positions of the captured entity text
                if start >= 0:
                    ctx_start = max(0, start - 40)
                    ctx_end = min(len(text), end + 40)
                    context = text[ctx_start:ctx_end]
                    if len(context.strip()) < 20:  # too short → probably noise
                        continue

                    injected.append({
                        "text": ent_text,
                        "label": learned_ent["label"],
                        "confidence": learned_ent["confidence"],
                        "gloss_en": learned_ent["canonical_en"],
                        "canonical_en": learned_ent["canonical_en"],
                        "start": start,
                        "end": end,
                        "injected": True,
                        "source": "knowledge_base"
                    })
                    detected_texts.add(ent_text)
                    logger.info(f"Injected entity from Knowledge Base: {ent_text} ({learned_ent['label']})")
        
        return injected

    def _is_non_latin(self, text: str) -> bool:
        """
        Detects if text contains non-ASCII characters.
        """
        return bool(re.search(r"[^\u0000-\u007F]", text))

# Singleton instance
entity_gloss_service = EntityGlossService()

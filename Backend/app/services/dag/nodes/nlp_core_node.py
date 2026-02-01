from app.services.dag.nodes.base_node import ProcessingNode, GateNode
from app.services.analysis.ner_service import ner_service
from app.services.analysis.keyword_extraction import keyword_extraction_service
import logging

logger = logging.getLogger(__name__)

class NERNode(ProcessingNode):
    """Extract entities from source text (before translation)"""
    
    def __init__(self):
        super().__init__("NER")

    def _process(self, context: dict) -> dict:
        # Get source text (Hindi/Marathi/etc - before translation)
        text = context.get("cleaned_text")
        if not text:
            context["entities_source"] = []
            logger.warning("No cleaned_text available for NER")
            return context
        
        # Extract entities from source language
        result = ner_service.extract_entities(text)
        entities = result.get("entities", [])
        
        # 🔑 ENRICH with glossing (adds canonical_en translations)
        from app.services.analysis.entity_gloss_service import entity_gloss_service
        entities = entity_gloss_service.enrich(entities)
        
        # Store as source entities (for TranslationNode to use)
        context["entities_source"] = entities
        
        # Backward compatibility - also set entities field
        existing = context.get("existing_entities", [])
        context["entities"] = entities if len(entities) >= len(existing) else existing
        
        logger.info(f"NER extracted {len(entities)} entities from source text")
        return context


class KeywordNode(ProcessingNode):
    def __init__(self):
        super().__init__("KeywordExtraction")

    def _process(self, context: dict) -> dict:
        # 🚀 Hybrid Strategy: KeyBERT needs English, Statistical/YAKE fine on source
        text = context.get("translated_text") if context.get("translated_to_en") else context.get("cleaned_text")
        if not text:
            return context

        result = keyword_extraction_service.extract(text, top_n=12)
        new_keywords = result.get("value", []) if isinstance(result, dict) else result
        
        # Normalize existing keywords (ensure they are strings)
        raw_existing = context.get("existing_keywords", [])
        existing = []
        for kw in raw_existing:
            if isinstance(kw, str):
                existing.append(kw)
            elif isinstance(kw, dict) and "text" in kw:
                existing.append(kw["text"])
        
        # Keep the richer set
        context["keywords"] = new_keywords if len(new_keywords) >= len(existing) else existing
        return context

class NLPQualityGate(GateNode):
    def __init__(self):
        super().__init__("NLPQualityGate")

    def _evaluate(self, context: dict) -> dict:
        entity_count = len(context.get("entities", []))
        keyword_count = len(context.get("keywords", []))
        
        # Coverage score
        score = (min(entity_count / 5, 1.0) * 0.6) + (min(keyword_count / 8, 1.0) * 0.4)
        context["scores"]["nlp_quality"] = score
        
        if score < 0.3:
            context["flags"].append("weak_nlp_results")
            if context["processing_mode"] == "full":
                context["processing_mode"] = "reduced"
                
        return context

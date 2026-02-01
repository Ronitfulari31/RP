import logging
from app.services.dag.nodes.base_node import ProcessingNode, GateNode
from app.services.analysis.translation_service import translation_service

logger = logging.getLogger(__name__)

class TranslationNode(ProcessingNode):
    def __init__(self):
        super().__init__("Translation")

    def _process(self, context: dict) -> dict:
        text = context["cleaned_text"]
        source_lang = context["language"]
        doc_id = context.get("document_id", "unknown")
        
        # Language Logic
        original_title = context.get("title", "")
        # Get target language from context, default to English for pipeline parity
        target_lang = context.get("target_lang", "en")
        
        if original_title:
            try:
                # Use generic translate_text for non-English targets or standard to_english
                if target_lang == "en":
                    title_res = translation_service.translate_to_english(original_title, source_lang)
                else:
                    title_res = {
                        "success": True, 
                        "translated_text": translation_service.translate_text(original_title, target_lang, source_lang),
                        "translation_engine": "generic"
                    }

                if title_res.get("success") and title_res["translated_text"] != original_title:
                    context["translated_title"] = title_res["translated_text"]
            except Exception as e:
                logger.warning(f"[{doc_id}] Title translation failed: {e}")

        # 2. Body Translation with ASCII Heuristic (Only if target is English)
        is_actually_english = True
        if target_lang == "en" and source_lang == 'en':
            non_ascii_chars = sum(1 for char in text[:500] if ord(char) > 127)
            if non_ascii_chars > 20:
                is_actually_english = False
                logger.info(f"[{doc_id}] marked 'en' but looks non-English. Translating...")

        if is_actually_english and source_lang == 'en' and target_lang == "en":
            context["translated_to_en"] = True
            context["translated_text"] = text
            context["scores"]["translation_quality"] = 1.0
            return context

        # Run service translation
        # 🚀 NLP Mode: Pipeline always uses greedy decoding for NER/Sentiment stability
        translation_mode = context.get("translation_mode", "nlp")
        context["translation_mode"] = translation_mode
        
        # 🔑 ENTITY MASKING: Prevent MT hallucination (e.g., रामलला → Ramallah)
        from app.services.analysis.entity_mask_service import entity_mask_service
        from app.services.analysis.entity_gloss_service import entity_gloss_service
        
        # Initialize gloss service with db if available (safe idempotent)
        if context.get("db") is not None and entity_gloss_service.db is None:
            entity_gloss_service.db = context["db"]
        
        entities = context.get("entities_source", [])
        
        # 🔑 INJECT MISSING ENTITIES: Fallback for entities NER might have missed
        entities = entity_gloss_service.inject_missing_entities(text, entities)
        context["entities_source"] = entities  # Update with injected entities
        context["entities"] = entities
        
        masked_text, entity_map = entity_mask_service.mask(text, entities)
        
        if target_lang == "en":
            # 🚀 Use pre-segmented sentences from Stage 1 if available
            sentences = context.get("sentences")
            
            # If we have sentences, we need to mask them too
            masked_sentences = None
            if sentences:
                masked_sentences = []
                for sent in sentences:
                    masked_sent, _ = entity_mask_service.mask(sent, entities)
                    masked_sentences.append(masked_sent)
            
            result = translation_service.translate_to_english(
                text=masked_text if not sentences else None,
                source_language=source_lang,
                sentences=masked_sentences,
                translation_mode=translation_mode
            )
        else:
            translated_text = translation_service.translate_text(masked_text, target_lang, source_lang)
            result = {
                "success": True if translated_text != "[Translation Failed]" else False,
                "translated_text": translated_text,
                "translation_engine": "generic"
            }
        
        if result.get("success"):
            # 🔑 REINJECT: Replace placeholders with canonical English forms
            translated_text = result["translated_text"]
            final_text = entity_mask_service.reinject(translated_text, entity_map)
            
            context.update({
                "translated_text": final_text,
                "translation_method": result["translation_engine"],
                "translated_to_en": True if target_lang == "en" else False
            })
            
            # 🚀 Fidelity Scoring (Step B)
            if context.get("entities_source"):
                from app.services.analysis.fidelity_service import fidelity_service
                score, _ = fidelity_service.calculate_fidelity(
                    context["entities_source"], 
                    final_text,
                    source_lang
                )
                context["scores"]["entity_fidelity"] = score
            
            # 🔑 AUTOMATIC ENTITY LEARNING: Save entities to knowledge base
            db = context.get("db")
            doc_id = context.get("document_id")
            if db is not None and doc_id:
                from app.services.analysis.entity_knowledge_service import entity_knowledge_service
                
                # Initialize knowledge service with db
                if entity_knowledge_service.db is None:
                    entity_knowledge_service.db = db
                
                # Learn each entity that was successfully translated
                for entity in entities:
                    entity_text = entity.get("text", "")
                    canonical_en = entity.get("canonical_en") or entity.get("gloss_en")
                    
                    if entity_text and canonical_en and entity.get("label"):
                        entity_knowledge_service.learn_entity(
                            entity_text=entity_text,
                            canonical_en=canonical_en,
                            label=entity["label"],
                            confidence=entity.get("confidence", 0.8),
                            context=text[:200],  # Store first 200 chars as context
                            doc_id=doc_id
                        )
            
            context["scores"]["translation_quality"] = 0.9
        else:
            context["translated_to_en"] = False
            context["scores"]["translation_quality"] = 0.0
            context["flags"].append("translation_failed_service_error")
            
        return context

class TranslationQualityGate(GateNode):
    def __init__(self):
        super().__init__("TranslationQualityGate")

    def _evaluate(self, context: dict) -> dict:
        score = context["scores"].get("translation_quality", 0.0)
        
        if score < 0.4:
            context["processing_mode"] = "embedding_only"
            context["flags"].append("translation_failed")
            # Fallback for translation failure
            if context.get("language") != "en":
                context["rejected"] = True
                context["rejection_reason"] = "Hard translation failure"
                context["rejected_at_node"] = self.name
        elif score < 0.7:
            context["processing_mode"] = "reduced"
            context["flags"].append("weak_translation")
            
        return context

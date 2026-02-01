import logging
import time
from typing import Dict, Any, Optional

from app.services.analysis.ner_service import ner_service
from app.services.analysis.translation_service import translation_service
from app.services.core.preprocessing import preprocessing_service
from app.services.analysis.fidelity_service import fidelity_service

logger = logging.getLogger(__name__)

GENERIC_ENTITY_LABELS = {"CITY", "OBJECT", "COMMON_NOUN"}

def deduplicate_by_canonical(entities):
    """
    Mask once per canonical entity, not per surface form.
    Industry systems deduplicate by the conceptual target to avoid alias noise.
    """
    seen = {}
    result = []

    for e in entities:
        # Prioritize gloss_en as the conceptual bridge for aliases
        # If 'Kashi' has gloss 'Varanasi', it will match 'Varanasi' itself.
        canonical = e.get("gloss_en") or e.get("canonical_en") or e.get("text")
        if canonical not in seen:
            seen[canonical] = e
            result.append(e)

    return result

def excessive_entity_density(text: str, entities: list) -> bool:
    """
    Safety net: No natural language contains 80 entities in a short snippet.
    If density is too high, it's likely a model hallucination/failure.
    """
    if not text or not entities:
        return False
    # Max 8 entities or 1 per 120 chars
    max_allowed = max(8, len(text) // 120)
    return len(entities) > max_allowed

def translate_with_entities(
    text: str,
    source_lang: str,
    target_lang: str = "en",
    translation_mode: str = "display",
    doc_id: Optional[str] = None,
    db=None
) -> Dict[str, Any]:
    """
    Orchestrates translation with entity preservation and automatic learning.
    Flow: Clean -> NER (Source) -> Translation -> Learn Entities -> Combine
    
    Args:
        text: Source text to translate
        source_lang: Source language code
        target_lang: Target language code
        translation_mode: 'nlp' or 'display'
        doc_id: Optional document ID for entity learning
        db: Optional MongoDB database for entity learning
    """
    start_time = time.time()
    
    # 1. Clean Text
    cleaned = preprocessing_service.clean_text(text)
    if not cleaned:
        return {
            "translated_text": "",
            "entities": [],
            "source_lang": source_lang,
            "target_lang": target_lang,
            "success": False,
            "error": "Empty text after cleaning"
        }

    # 2. NER on SOURCE language (Gold Standard)
    # This prevents entity drift (e.g., Ramlalla -> Ramallah)
    ner_result = ner_service.extract_entities(cleaned, source_lang=source_lang)
    ner_entities_raw = ner_result.get("entities", [])
    entities_source = list(ner_entities_raw) # Start with raw detections
    
    # 🔑 INITIALIZE KNOWLEDGE SERVICES
    from app.services.analysis.entity_gloss_service import entity_gloss_service
    from app.services.analysis.entity_knowledge_service import entity_knowledge_service
    
    # Initialize services with db if available (avoid per-request mutation of singleton)
    if db is not None:
        if hasattr(entity_gloss_service, 'set_db'):
            entity_gloss_service.set_db(db)
        elif entity_gloss_service.db is None:
            entity_gloss_service.db = db
        
        if hasattr(entity_knowledge_service, 'set_db'):
            entity_knowledge_service.set_db(db)
        elif entity_knowledge_service.db is None:
            entity_knowledge_service.db = db
    
    # 🔑 ADD GLOSSING (Step A)
    entities_source = entity_gloss_service.enrich(entities_source)
    
    # 🔑 INJECT MISSING ENTITIES: Fallback for entities NER might have missed
    entities_source = entity_gloss_service.inject_missing_entities(cleaned, entities_source)

    # ️ NEW: STRUCTURAL VALIDATION (Pre-Masking)
    # Replaces hardcoded blacklists with statistical/script-aware signals
    from app.services.analysis.entity_span_validator import entity_span_validator
    validated_entities = [
        e for e in entities_source 
        if entity_span_validator.is_valid_for_masking(
            e.get("text", ""), 
            source_lang,
            start=e.get("start"),
            end=e.get("end"),
            original_text=cleaned
        )
    ]

    # 🚀 Fix 3: Optimized Batch Translation Invariance Check
    # Ensure masking the entity doesn't break the sentence structure
    if validated_entities:
        try:
            # 1. Get baseline (one call)
            baseline_res = translation_service.translate_to_english(text=cleaned, source_language=source_lang, translation_mode="nlp")
            baseline = baseline_res.get("translated_text", "")
            
            if baseline:
                # 2. Prepare masked versions
                candidates = validated_entities
                masked_list = [cleaned.replace(e.get("text", ""), "__ENT__", 1) for e in candidates]
                
                # 3. Batch translate
                translated_masked = translation_service.translate_batch(masked_list, target_lang="en", source_lang=source_lang, translation_mode="nlp")
                
                deep_validated = []
                set1 = set(baseline.lower().split())
                
                for i, ent in enumerate(candidates):
                    t2 = translated_masked[i].replace("__ENT__", ent.get("text", ""))
                    set2 = set(t2.lower().split())
                    
                    if not set1:
                        deep_validated.append(ent)
                        continue
                        
                    intersection = len(set1 & set2)
                    similarity = intersection / len(set1)
                    
                    if similarity > 0.6:
                        deep_validated.append(ent)
                    else:
                        logger.debug(f"[INVARIANCE] Rejecting grammar-sensitive span: {ent.get('text')}")
                
                validated_entities = deep_validated
        except Exception as e:
            logger.warning(f"Batch invariance check failed: {e}")

    # 🛡️ NEW: ATOMIC ENTITY RESOLUTION (Split compounds)
    from app.services.analysis.atomic_entity_resolver import atomic_entity_resolver
    resolved_entities = []
    for ent in validated_entities:
        parts = atomic_entity_resolver.split(ent.get("text", ""))
        for p in parts:
            resolved_entities.append({
                **ent,
                "text": p,
                "positions_approximate": True  # Mark that positions are no longer accurate after splitting
            })
    validated_entities = resolved_entities

    # 🛡️ NEW: CANONICAL DEDUPLICATION (Fix Issue 1: Alias Duplication)
    # Mask once per concept, not per surface form.
    validated_entities = deduplicate_by_canonical(validated_entities)

    # 🚀 Fix 4: Entity Density Guard
    # If noise is still too high, disable masking to prevent garbage output
    if excessive_entity_density(cleaned, validated_entities):
        logger.warning(f"[DENSITY_GUARD] Too many entities ({len(validated_entities)}). Disabling masking for this run.")
        entities_to_mask = []
        validated_entities = [] # Kill them for the return response too
    else:
        # 🛡️ OPTIONAL: PERSON MASKING SKIP (Improve News Readability)
        # In 'display' mode, we often skip masking persons to keep the flow natural.
        if translation_mode == "display":
            entities_to_mask = [
                e for e in validated_entities
                if not e.get("label", "").startswith("PERSON")
            ]
        else:
            entities_to_mask = validated_entities

    # 🔑 ENTITY MASKING: Prevent MT hallucination
    from app.services.analysis.entity_mask_service import entity_mask_service
    masked_text, entity_map = entity_mask_service.mask(cleaned, entities_to_mask, source_lang=source_lang)

    # 3. Translation
    # Use 'display' mode for fluent English or 'nlp' for literal mapping
    if target_lang == "en":
        trans_res = translation_service.translate_to_english(
            text=masked_text,
            source_language=source_lang,
            translation_mode=translation_mode
        )
        translated_text = trans_res.get("translated_text", "[Translation Failed]")
    else:
        # For non-English targets, call translate_text and wrap in structured response
        translated_text = translation_service.translate_text(
            masked_text, target_lang, source_lang, translation_mode
        )
        trans_res = {
            "text": translated_text,
            "translated_text": translated_text,
            "success": bool(translated_text and translated_text != "[Translation Failed]"),
            "error": None if (translated_text and translated_text != "[Translation Failed]") else "Translation failed"
        }

    # 🔑 REINJECT: Replace placeholders with canonical English forms
    final_text = entity_mask_service.reinject(translated_text, entity_map)

    # 🔑 AUTOMATIC ENTITY LEARNING: Save entities to knowledge base
    if db is not None and doc_id and trans_res.get("success"):
        from app.services.analysis.entity_knowledge_service import entity_knowledge_service
        
        # Initialize knowledge service with db
        if entity_knowledge_service.db is None:
            entity_knowledge_service.db = db
        
        # Learn each entity that was successfully translated
        is_cjk = source_lang.split("-")[0].lower() in ["zh", "ja", "ko"]

        for entity in validated_entities:
            entity_text = entity.get("text", "")
            canonical_en = entity.get("canonical_en") or entity.get("gloss_en")
            
            if entity_text and canonical_en and entity.get("label"):
                # 🛡️ FIX D: Block "source-to-source" learning for CJK
                # If we couldn't find an English canonical, don't pollute KB with the Chinese text
                if is_cjk and entity_text == canonical_en:
                    logger.debug(f"Skipping KB learning for Untranslated CJK: {entity_text}")
                    continue

                entity_knowledge_service.learn_entity(
                    entity_text=entity_text,
                    canonical_en=canonical_en,
                    label=entity["label"],
                    confidence=entity.get("confidence", 0.8),
                    context=cleaned[:200],  # Store first 200 chars as context
                    doc_id=doc_id
                )

    # 3.5 Fidelity Scoring (Step B)
    fidelity_score, missing = fidelity_service.calculate_fidelity(
        validated_entities, final_text, source_lang
    )

    total_time = (time.time() - start_time) * 1000

    # 4. Enriched Response
    return {
        "success": trans_res.get("success", False),
        "translated_text": final_text,
        "entities": validated_entities, # ✅ Only returns TRUE production-grade entities
        "source_lang": source_lang,
        "target_lang": target_lang,
        "metadata": {
            "translation_mode": translation_mode,
            "entity_source": "pre_translation",
            "ner_role": ner_result.get("role"),
            "ner_count": len(ner_entities_raw),
            "validated_entity_count": len(validated_entities),
            "translation_engine": trans_res.get("translation_engine", "generic"),
            "entity_fidelity": fidelity_score,
            "entities_missing": missing,
            "total_time_ms": round(total_time, 2)
        }
    }

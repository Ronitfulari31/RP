import unicodedata
import logging
from app.services.dag.nodes.base_node import ProcessingNode, GateNode
from app.services.core.preprocessing import preprocessing_service

logger = logging.getLogger(__name__)

def normalize_text(text) -> str:
    if not text:
        return ""
    return unicodedata.normalize("NFKC", str(text)).strip()

def resolve_language(context, detected_language):
    stored_lang = context.get("language")
    
    # 1. Check Auto-Detection with High Confidence (Trust V2 GPU)
    if isinstance(detected_language, dict):
        det_val = detected_language.get("value", "unknown")
        det_conf = detected_language.get("confidence", 0.0)
        
        # If V2 is very confident, trust it over metadata (RSS feeds often mislabel headers)
        if det_val != "unknown" and det_conf > 0.85:
            return det_val

        # If we have a decent detection and NO metadata, use detection
        if det_val != "unknown" and (not stored_lang or stored_lang == "unknown"):
            return det_val

    # 2. Fallback to Metadata (RSS/Source)
    if isinstance(stored_lang, list) and len(stored_lang) > 0:
        return stored_lang[0]
    
    if isinstance(stored_lang, str) and stored_lang and stored_lang != "unknown":
        return stored_lang
    
    # 3. Last Resort: Weak detection
    if isinstance(detected_language, dict):
         return detected_language.get("value", "unknown")
    if detected_language and detected_language != "unknown":
        return detected_language
        
    return "unknown"

class PreprocessingNode(ProcessingNode):
    def __init__(self):
        super().__init__("Preprocessing")

    def _process(self, context: dict) -> dict:
        raw_text = context["raw_text"]
        result = preprocessing_service.preprocess(raw_text)
        
        # 1. Resolve Language
        final_lang = resolve_language(context, result.get("language"))
        
        # 2. Use Cleaned Text (Already normalized and cleaned in service)
        clean_text = result.get("clean_text", raw_text)
        
        context.update({
            "cleaned_text": clean_text,
            "language": final_lang,
            "content_hash": result.get("text_hash", ""),
            "sentences": result.get("sentences", []),
            "segmentation_metadata": result.get("segmentation", {}),
            "quality_score": result.get("quality_score", 0.0),
            "passed": result.get("passed", False)
        })
        
        confidence = 1.0 if final_lang != "unknown" else 0.4
        logger.info(f"Language Confidence: {confidence} (Final: {final_lang})")
        context["scores"]["language_confidence"] = confidence
        return context

class DeduplicationGate(GateNode):
    def __init__(self):
        super().__init__("DeduplicationGate")

    def _evaluate(self, context: dict) -> dict:
        return context

class LanguageConfidenceGate(GateNode):
    def __init__(self):
        super().__init__("LanguageConfidenceGate")

    def _evaluate(self, context: dict) -> dict:
        conf = context["scores"].get("language_confidence", 0.0)
        if conf < 0.5:
            context["rejected"] = True
            context["rejection_reason"] = "Low language confidence"
            context["rejected_at_node"] = self.name
        elif conf < 0.8:
            context["flags"].append("language_warning")
        return context

class TextQualityGate(GateNode):
    def __init__(self):
        super().__init__("TextQualityGate")

    def _evaluate(self, context: dict) -> dict:
        # Use existing quality markers from PreprocessingService
        score = context.get("quality_score", 0.0)
        passed = context.get("passed", False)
        
        context["scores"]["text_quality"] = score
        
        if not passed:
            context["rejected"] = True
            context["rejection_reason"] = f"Text quality gate failed (Score: {score:.3f})"
            context["rejected_at_node"] = self.name
        elif score < 0.6:
            context["flags"].append("text_quality_warning")
            
        return context

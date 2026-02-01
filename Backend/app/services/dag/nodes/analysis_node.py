import logging
from app.services.dag.nodes.base_node import ProcessingNode, GateNode
from app.services.analysis.location_extraction import location_extraction_service
from app.services.analysis.summarization import summarization_service
from app.services.analysis.sentiment_service import get_sentiment_service
from app.services.analysis.classification.category_classifier import classify_category

logger = logging.getLogger(__name__)

# 🌍 Country to Continent Mapping
COUNTRY_TO_CONTINENT = {
    "india": "asia",
    "china": "asia",
    "pakistan": "asia",
    "bangladesh": "asia",
    "usa": "americas",
    "united states": "americas",
    "canada": "americas",
    "united kingdom": "europe",
    "uk": "europe",
    "france": "europe",
    "germany": "europe",
    "australia": "oceania",
    "brazil": "americas",
    "japan": "asia",
    "south korea": "asia"
}

def apply_domain_guardrails(category, event_type, confidence):
    if confidence < 0.2:
        return "other", 0.0

    if category == "sports" and event_type in {
        "terror_attack", "crime", "war", "natural_disaster"
    }:
        logger.warning(f"[GUARD] Blocked cross-domain event '{event_type}' for sports article")
        return "other", 0.0

    return event_type, confidence

class CategoryNode(ProcessingNode):
    def __init__(self):
        super().__init__("CategoryClassification")

    def _process(self, context: dict) -> dict:
        # 🧠 FIX 3: Idempotency Guard
        if context.get("category") and context.get("category") != "unknown":
            logger.info("Category already exists. Skipping classification.")
            return context

        text = context["translated_text"] if context["translated_to_en"] else context["cleaned_text"]
        result = classify_category(text)
        
        # Apply Guardrails
        current_category = context.get("category") or context.get("metadata", {}).get("category")
        safe_type, safe_conf = apply_domain_guardrails(
            current_category, result.get("primary"), result.get("confidence", 0.0)
        )
        
        # COMPETITIVE MERGING: Keep existing if more confident
        existing_conf = context.get("existing_category_conf", 0.0)
        if existing_conf > safe_conf:
            safe_type = context.get("existing_category", safe_type)
            safe_conf = existing_conf

        context["event"] = {
            "type": safe_type,
            "confidence": safe_conf,
            "classification_time": result.get("analysis_time", 0.0)
        }
        
        # For backward compatibility with routes
        context["category"] = safe_type
        context["scores"]["category_confidence"] = safe_conf
        return context

class CategoryConfidenceGate(GateNode):
    def __init__(self):
        super().__init__("CategoryConfidenceGate")

    def _evaluate(self, context: dict) -> dict:
        conf = context["scores"].get("category_confidence", 0.0)
        if conf < 0.5:
            # context["category"] = "general" # V1 doesn't force 'general'
            context["flags"].append("low_category_confidence")
        return context

class LocationNode(ProcessingNode):
    def __init__(self):
        super().__init__("LocationExtraction")

    def _process(self, context: dict) -> dict:
        # 🧠 FIX 3: Idempotency Guard (If locations dict is already populated with meaningful data)
        if context.get("locations") and any(v != "Unknown" for k, v in context["locations"].items() if k in ["city", "country"]):
            logger.info("Meaningful locations already exist. Skipping extraction.")
            return context

        # 🚀 Use source entities for higher-accuracy location extraction if available
        text = context.get("translated_text") if context.get("translated_to_en") else context.get("cleaned_text")
        
        result = location_extraction_service.extract_locations(text) or {}
        raw_loc = result.get("enriched_location") or result.get("normalized") or result.get("location") or {}
        
        country = raw_loc.get("country", "Unknown")
        final_country = country.lower().strip() if country else "global"
        
        # 🟢 FEEDBACK FIX: Handle common geocoding typos/artifacts
        if final_country == "iindia":
            final_country = "india"
        new_conf = raw_loc.get("confidence", 0.0)
         
        # COMPETITIVE MERGING: Keep existing if more confident
        existing_loc = context.get("existing_locations") or {}
        existing_conf = existing_loc.get("confidence", 0.0) if isinstance(existing_loc, dict) else 0.0
        
        if existing_conf > new_conf:
            context["locations"] = existing_loc
        else:
            context["locations"] = {
                "city": raw_loc.get("city", "Unknown"),
                "state": raw_loc.get("state", "Unknown"),
                "country": final_country,
                "continent": COUNTRY_TO_CONTINENT.get(final_country, "global"),
                "confidence": new_conf
            }
        
        # V1 logic for country/continent sync
        context["country"] = context["locations"].get("country", final_country)
        context["continent"] = context["locations"].get("continent", "global")
        
        return context

class SummaryNode(ProcessingNode):
    def __init__(self):
        super().__init__("Summarization")

    def _process(self, context: dict) -> dict:
        # 🧠 FIX 3: Idempotency Guard
        if context.get("summary") and (isinstance(context["summary"], str) or context["summary"].get("en")):
            logger.info("Summary already exists. Skipping generation.")
            return context

        text = context["translated_text"] if context["translated_to_en"] else context["cleaned_text"]
        res = summarization_service.summarize(text, method="auto")
        summary = res.get("value", "")
        
        # Store as object for frontend compatibility (matches ArticleDetail expectations)
        context["summary"] = {"en": summary}
        
        if context.get("language") != "en":
            context["translated_summary"] = {"en": summary} # Legacy key if needed
            
        # Calculate reduction percentage
        orig_len = len(text) if text else 1
        summ_len = len(summary) if summary else 0
        reduction = round((1 - (summ_len / orig_len)) * 100, 1) if orig_len > 0 else 0
        
        context["scores"]["summary_quality"] = 0.8 if len(summary) > 50 else 0.3
        context["scores"]["reduction_percentage"] = reduction
        
        return context

class SummaryQualityGate(GateNode):
    def __init__(self):
        super().__init__("SummaryQualityGate")

    def _evaluate(self, context: dict) -> dict:
        if context["scores"].get("summary_quality", 0.0) < 0.4:
            context["flags"].append("weak_summary")
        return context

class SentimentNode(ProcessingNode):
    def __init__(self):
        super().__init__("SentimentAnalysis")

    def _process(self, context: dict) -> dict:
        # 🧠 FIX 3: Idempotency Guard
        if context.get("sentiment") and context["sentiment"].get("method") != "uninitialized":
            logger.info("Sentiment already analyzed. Skipping.")
            return context

        english_text = context["translated_text"] if context["translated_to_en"] else context["cleaned_text"]
        summary_data = context.get("summary")
        summary_text = ""
        if isinstance(summary_data, dict):
            summary_text = summary_data.get("en", "")
        else:
            summary_text = str(summary_data or "")
            
        sentiment_service = get_sentiment_service()
        result = sentiment_service.analyze(
            cleaned_text=english_text,
            summary_text=summary_text,
            raw_text=english_text,
            method="auto"
        )
        
        new_sentiment = {
            "sentiment": result.get("value", "neutral"),
            "confidence": result.get("confidence", 0.0),
            "method": result.get("status", "unknown"),
            "scores": result.get("raw_scores", {}),
            "analysis_time": result.get("analysis_time", 0.0)
        }

        # COMPETITIVE MERGING: Keep existing if more confident
        existing = context.get("existing_sentiment") or {}
        existing_conf = existing.get("confidence", 0.0) if isinstance(existing, dict) else 0.0
        
        context["sentiment"] = new_sentiment if result["confidence"] >= existing_conf else existing
        return context

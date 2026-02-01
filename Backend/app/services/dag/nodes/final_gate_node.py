from app.services.dag.nodes.base_node import GateNode

class FinalQualityGate(GateNode):
    def __init__(self):
        super().__init__("FinalQualityGate")

    def _evaluate(self, context: dict) -> dict:
        scores = context["scores"]
        
        # Weighted overall score
        weights = {
            "text_quality": 0.20,
            "translation_quality": 0.15,
            "nlp_quality": 0.25,
            "category_confidence": 0.15,
            "summary_quality": 0.15,
            "language_confidence": 0.10
        }
        
        overall = sum(scores.get(k, 0.0) * w for k, w in weights.items())
        
        # Adjust for embedding presence (mandatory)
        if context.get("embedding") is None:
            overall *= 0.5
            
        context["scores"]["overall"] = overall
        
        # Lower threshold for translated articles (category detection is weaker)
        is_translated = context.get("translated_to_en", False) and context.get("language") != "en"
        min_threshold = 0.35 if is_translated else 0.45
        
        if overall < min_threshold:
            context["rejected"] = True
            context["rejection_reason"] = f"Overall quality too low: {overall:.2f} (threshold: {min_threshold})"
            context["rejected_at_node"] = self.name
            
        # Tiering
        context["tier"] = 1 if overall >= 0.85 else 2 if overall >= 0.70 else 3
        
        return context

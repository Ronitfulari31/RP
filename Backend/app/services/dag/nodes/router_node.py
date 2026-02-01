from app.services.dag.nodes.base_node import RouterNode

class LanguageRouter(RouterNode):
    def __init__(self):
        super().__init__("LanguageRouter")

    def _route(self, context: dict) -> str:
        lang = context.get("language", "unknown")
        return "translate" if lang != "en" and lang != "unknown" else "skip_translation"

class ProcessingModeRouter(RouterNode):
    def __init__(self):
        super().__init__("ProcessingModeRouter")

    def _route(self, context: dict) -> str:
        # Decisions based on translation quality or text quality
        return context.get("processing_mode", "full")

class FinalActionRouter(RouterNode):
    def __init__(self):
        super().__init__("FinalActionRouter")

    def _route(self, context: dict) -> str:
        # 🧠 FIX 3: Idempotency Guard (If tier already decided, skip)
        if context.get("tier") and context.get("tier") in [1, 2, 3]:
            # Map tier back to route key
            tier_map = {1: "high_tier", 2: "mid_tier", 3: "low_tier"}
            return tier_map.get(context["tier"], "mid_tier")

        if context.get("rejected"):
            return "reject"
        
        score = context["scores"].get("overall", 0.0)
        if score >= 0.85:
            return "high_tier"
        elif score >= 0.70:
            return "mid_tier"
        else:
            return "low_tier"

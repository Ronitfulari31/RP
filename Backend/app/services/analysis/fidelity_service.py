import logging
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)

class FidelityService:
    def calculate_fidelity(self, entities_source: List[Dict], translated_text: str, source_lang: str) -> Tuple[float, List[str]]:
        """
        Calculates how many source entities are preserved in the translation.
        Matches micro-translated versions of entities against the final text.
        """
        if not entities_source:
            return 1.0, []

        if not translated_text:
            return 0.0, [ent.get("text") for ent in entities_source if ent.get("text")]

        matched_count = 0
        missing_entities = []

        try:
            from rapidfuzz import fuzz
        except ImportError:
            # Simple fallback if rapidfuzz fails to load
            fuzz = None

        translated_lower = translated_text.lower()
        processed_count = 0  # Track number of entities actually checked

        for ent in entities_source:
            source_text = ent.get("text", "").strip()
            if not source_text:
                continue

            processed_count += 1  # Increment only for non-empty entities
            canonical = ent.get("canonical_en") or ent.get("gloss_en") or source_text
            expected = canonical.lower()

            # Require reasonably strong substring presence
            if expected in translated_lower:
                matched_count += 1
            elif fuzz and fuzz.partial_ratio(expected, translated_lower) > 88:
                matched_count += 1
            else:
                # Also check original text presence (sometimes kept)
                orig = source_text.lower()
                if orig in translated_lower:
                    matched_count += 1
                elif fuzz and fuzz.partial_ratio(orig, translated_lower) > 88:
                    matched_count += 1
                else:
                    missing_entities.append(source_text)

        # Use processed_count for accurate score (only entities that were checked)
        score = round(matched_count / processed_count, 2) if processed_count else 1.0

        # 🚀 Fix 4: Penalize if too many entities were detected (over-detection signal)
        if processed_count > 40:
            logger.warning(f"[FIDELITY] Excessive entity count ({processed_count}). Penalizing score.")
            score = round(score * 0.4, 2)

        # Never blindly give 100% to CJK anymore
        return score, missing_entities

fidelity_service = FidelityService()

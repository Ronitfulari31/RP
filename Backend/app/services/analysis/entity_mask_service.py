"""
Entity Mask Service
Masks source-language entities before translation
and safely reinjects canonical English forms after translation.
"""

import re
import logging
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)


class EntityMaskService:
    """
    Masks source-language entities before translation
    and safely reinjects canonical English forms after translation.
    """

    def mask(
        self,
        text: str,
        entities: List[Dict],
        source_lang: str = "en"
    ) -> Tuple[str, Dict[str, Dict]]:
        """
        Replace entity surface forms with placeholders.
        """
        if not entities:
            return text, {}

        masked_text = text
        entity_map = {}
        idx = 0

        # Sort by length DESC to avoid partial overlaps
        entities_sorted = sorted(
            entities, key=lambda e: len(e.get("text", "")), reverse=True
        )

        for ent in entities_sorted:
            src = ent.get("text")
            if not src or src not in masked_text:
                continue

            # ENTITY_N format
            key = f"ENTITY_{idx}"
            placeholder = f"[{key}]"
            idx += 1

            masked_text = masked_text.replace(src, placeholder)

            entity_map[key] = {
                "source": src,
                "canonical_en": ent.get("gloss_en") or ent.get("canonical_en") or src,
                "label": ent.get("label"),
            }

        return masked_text, entity_map

    def reinject(self, translated_text: str, entity_map: Dict[str, Dict]) -> str:
        """
        Replace placeholders with canonical English forms.
        Highly resilient to MT mutations (stripping ITY, changing underscores, etc).
        """
        if not entity_map:
            return translated_text

        final_text = translated_text
        
        # Sort keys descending to avoid sub-string replacement issues (ENTITY_10 vs ENTITY_1)
        try:
            sorted_keys = sorted(entity_map.keys(), key=lambda k: int(k.split('_', 1)[1]), reverse=True)
        except (IndexError, ValueError):
            # Fallback: skip malformed keys or assign fallback numeric value
            sorted_keys = []
            for k in entity_map.keys():
                try:
                    parts = k.split('_', 1)
                    if len(parts) == 2 and parts[1].isdigit():
                        sorted_keys.append(k)
                    # Skip invalid keys
                except Exception:
                    pass
            sorted_keys.sort(key=lambda k: int(k.split('_')[1]), reverse=True)

        for key in sorted_keys:
            meta = entity_map[key]
            val = meta['canonical_en']
            idx = key.split('_')[1]
            
            # THE ULTIMATE RESILIENT PATTERN:
            # Matches: [ENTITY_0], [ENT_0], [ENT 0], [ENTITY 0], ENTITY_0, ENT_0, ENTITY0, ENT0
            # Also captures mutations like [इकाई 3], (ENTITY 3), or just entity3
            pattern = re.compile(rf"(?:\[|\()?\s*ENT(?:ITY|ITY_)?[\s_]*{idx}\s*(?:\]|\))?", re.IGNORECASE)
            
            if pattern.search(final_text):
                logger.info(f"[REINSERT] Match found for {key} ({idx}) -> {val}")
                # Use callable for literal replacement (handles special characters in val)
                final_text = pattern.sub(lambda m: val, final_text)
            else:
                # TRIPLE-SAFETY: If MT translated "ENTITY" or "ENT", try a last-ditch numeric search if text has changed
                # Only if the index is unique enough (e.g. 5+ index)
                logger.warning(f"[REINSERT] No match found text-wide for {key} (index {idx}). Pattern: {pattern.pattern}")
                # Optional: log a snippet of final_text to see what MT did
                snippet = final_text[:500] + "..." if len(final_text) > 500 else final_text
                logger.debug(f"[REINSERT] Current Text Snippet: {snippet}")

        # 🔒 Cleanup ANY remaining potential placeholders (Safety net)
        placeholder_pattern = r"(?:\[\s*)?ENT(?:ITY)?[\s_]*\d+(?:\s*\])?"
        remaining_matches = re.findall(placeholder_pattern, final_text, flags=re.IGNORECASE)
        if remaining_matches:
            logger.warning(f"[REINSERT] Warning: Found unmatched placeholders: {remaining_matches}")
        
        final_text = re.sub(placeholder_pattern, "", final_text, flags=re.IGNORECASE)

        # Final cleanup: Remove double spaces and strip
        final_text = re.sub(r"\s+", " ", final_text).strip()
        
        return final_text


# Singleton
entity_mask_service = EntityMaskService()

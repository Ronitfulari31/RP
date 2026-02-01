import unicodedata
import re
import logging

logger = logging.getLogger(__name__)

class AtomicEntityResolver:
    """
    Splits compound NER spans into atomic entities
    using structural cues (not hard-coded words).
    """

    def split(self, text: str):
        """
        Returns list of atomic entity candidates.
        """
        if not text:
            return []

        # Split on structural separators (Unicode-aware)
        # Includes common commas, Chinese separators (、), and ampersands
        parts = re.split(r"[、,，&]| and | 和 ", text)

        atomic = []
        for part in parts:
            cleaned = part.strip()
            if self._looks_like_name(cleaned):
                atomic.append(cleaned)

        return atomic

    def _looks_like_name(self, text: str) -> bool:
        """
        Structural name-likeness check.
        """
        if not text:
            return False

        # Atomic cap: Most names across scripts are under 12 chars
        # (Allows compound growth in masking but protects KB)
        if len(text) > 12:
            return False

        # Punctuation heavy → not a name (e.g., "Part A: Part B")
        punct_ratio = sum(
            1 for c in text if unicodedata.category(c).startswith("P")
        ) / max(len(text), 1)

        if punct_ratio > 0.1:
            return False

        return True

# Singleton instance
atomic_entity_resolver = AtomicEntityResolver()

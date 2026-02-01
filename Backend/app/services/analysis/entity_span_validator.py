import unicodedata
import re
import logging

# Attempt to import regex for Unicode property support, fallback to re
try:
    import regex as _re
except ImportError:
    import re as _re

logger = logging.getLogger(__name__)

class EntitySpanValidator:
    """
    Industry-style, non-hardcoded entity span validation.
    Uses structural and statistical signals instead of keywords.
    """

    def is_clean_span(self, text: str, start: int, end: int) -> bool:
        """
        Universal boundary check:
        Ensures entities don't cut through words or letters.
        """
        # Characters before and after span (with bounds checking)
        before = text[start - 1] if start > 0 else ""
        after = text[end] if end < len(text) else ""

        try:
            # Try using \p{L} and \p{N} with regex module
            # Verify bounds before accessing text indices
            if start < len(text) and _re.match(r"\p{L}|\p{N}", before) and _re.match(r"\p{L}|\p{N}", text[start]):
                return False
            if end > 0 and end <= len(text) and _re.match(r"\p{L}|\p{N}", after) and _re.match(r"\p{L}|\p{N}", text[end - 1]):
                return False
        except (re.error, TypeError, AttributeError):
            # Fallback to stdlib re with character class checks via unicodedata
            # Safely check bounds before accessing text
            before_is_alnum = before.isalpha() or before.isdigit() if before else False
            after_is_alnum = after.isalpha() or after.isdigit() if after else False
            start_is_alnum = text[start].isalpha() or text[start].isdigit() if start < len(text) else False
            end_is_alnum = text[end - 1].isalpha() or text[end - 1].isdigit() if (end > 0 and end <= len(text)) else False
            
            if before_is_alnum and start_is_alnum:
                return False
            if after_is_alnum and end_is_alnum:
                return False

        return True

    def passes_roundtrip(self, text: str, ent_text: str) -> bool:
        """
        Structural stability check:
        If masking and restoring changes the string, it's a grammar-dependent phrase, not a name.
        """
        if not ent_text or ent_text not in text:
            return False

        marker = "__X__"
        # We replace the first occurrence only for the test
        masked = text.replace(ent_text, marker, 1)
        restored = masked.replace(marker, ent_text, 1)

        return restored == text

    def is_valid_for_masking(self, text: str, lang: str, start: int = None, end: int = None, original_text: str = None) -> bool:
        """
        Soft validation:
        - Prevents obvious clause-like spans
        - Keeps translation safe
        """
        if not text:
            return False

        # 🚀 Fix 5: Hard Minimum Length (No 1-4 char fragments)
        if len(text) < 5:
            return False
        if self._is_no_whitespace_script(lang) and len(text) < 6:
            return False

        # 🚀 Fix 1: Round-trip Stability (Primary Filter)
        if original_text and not self.passes_roundtrip(original_text, text):
            return False

        # 🚀 Fix 2: Clean Boundary Alignment
        if original_text and start is not None and end is not None:
            if not self.is_clean_span(original_text, start, end):
                return False

        # Universal absolute cap (prevents whole sentences)
        if len(text) > 40:
            return False

        # Script-aware tighter cap (CJK, Thai, Japanese)
        if self._is_no_whitespace_script(lang) and len(text) > 10:
            return False

        # Punctuation density check
        if self._punctuation_ratio(text) > 0.15:
            return False

        return True

    def is_valid_for_learning(self, text: str, lang: str, confidence: float) -> bool:
        """
        Hard validation:
        - Protects Knowledge Base
        """
        if not self.is_valid_for_masking(text, lang):
            return False

        # Confidence gate
        if confidence < 0.6:
            return False

        # Function-word dominance check
        if self._function_char_ratio(text) > 0.35:
            return False

        return True

    # ------------------- helpers -------------------

    def _punctuation_ratio(self, text: str) -> float:
        punct = sum(1 for c in text if unicodedata.category(c).startswith("P"))
        return punct / max(len(text), 1)

    def _function_char_ratio(self, text: str) -> float:
        """
        Approximates function words without POS tagging.
        High ratio => sentence-like.
        """
        # Counting categories like: 
        # Pd (Dash), Pc (Connector), Po (Other punct), Zs (Space)
        function_like = sum(
            1 for c in text
            if unicodedata.category(c) in {"Pd", "Pc", "Po", "Zs"}
        )
        return function_like / max(len(text), 1)

    def _is_no_whitespace_script(self, lang: str) -> bool:
        if not lang:
            return False
        return lang.startswith(("zh", "ja", "th"))

# Singleton instance
entity_span_validator = EntitySpanValidator()

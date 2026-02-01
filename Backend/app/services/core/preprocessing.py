"""
Preprocessing Service
Handles language detection, text cleaning, and duplicate detection
(Language-agnostic & Unicode-safe)
"""

import re
import os
import hashlib
import logging
import unicodedata
import threading
# torch import moved to local scope for performance
from typing import Dict, Any
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from langdetect import detect, LangDetectException

logger = logging.getLogger(__name__)


class PreprocessingService:
    """Service for text preprocessing operations"""

    def __init__(self):
        # BROAD emoji and symbol pattern (Unicode 6.0+ safe)
        self.emoji_pattern = re.compile(
            r"["
            r"\U0001F000-\U0001FAFF" # Emoticons, Symbols, Pictographs, Transport, Flags
            r"\U00002700-\U000027BF" # Dingbats
            r"\U00002600-\U000026FF" # Misc Symbols
            r"]+",
            flags=re.UNICODE
        )

        # ----------------------------------------------------
        # JUNK FILTERS (Noise removal for better NLP)
        # ----------------------------------------------------
        self.junk_patterns = [
            # Spanish leftovers
            re.compile(r"Tu suscripción se está usando.*", re.IGNORECASE),
            re.compile(r"Disponible en todas las plataformas.*", re.IGNORECASE),
            re.compile(r"Escúchanos en.*", re.IGNORECASE),
            
            # Global Metadata & Copyrights
            re.compile(r"©\s*Copyright.*", re.IGNORECASE),
            re.compile(r"All rights reserved.*", re.IGNORECASE),
            re.compile(r"Read more.*", re.IGNORECASE),
            re.compile(r"Subscribe to.*", re.IGNORECASE),
            
            # Identifiers
            re.compile(r"\b\d{9,12}\b"),              # Phone-like numbers
            re.compile(r"[\w\.-]+@[\w\.-]+\.\w+"),    # Improved Email regex
        ]

        # ----------------------------------------------------
        # OPTIMIZED REGEX (Pre-compiled for performance)
        # ----------------------------------------------------
        self.url_pattern = re.compile(r"http[s]?://\S+", re.IGNORECASE)
        self.html_pattern = re.compile(r"<[^>]+>")
        self.punctuation_map = {
            '\u201c': '"', '\u201d': '"', # Smart double quotes
            '\u2018': "'", '\u2019': "'", # Smart single quotes
            '\u2014': ' - ', '\u2013': ' - ', # Em/En dashes
            '--': ' - '
        }

        # ----------------------------------------------------
        # SEGMENTATION (Lazy-loaded pySBD)
        # ----------------------------------------------------
        self._segmenters = {} # Cache for pySBD segmenters

        # ----------------------------------------------------
        # V2 Language Model (Transformer GPU) - Drive D Only
        # ----------------------------------------------------
        try:
            import torch
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            self.device = "cpu"
        self._lid_model = None
        self._lid_tokenizer = None
        self._lid_attempted = False
        self._load_lock = threading.Lock()
    
    def _load_lid_v2(self):
        """Lazy load the Transformer-based LID model (Tier 1 GPU)"""
        with self._load_lock:
            if self._lid_attempted:
                return
            self._lid_attempted = True

        # Skip GPU model loading if environment variable is set (for fast audit/testing)
        if os.environ.get("SKIP_GPU_LID") == "1":
            logger.info("Skipping GPU LID model (SKIP_GPU_LID=1), using langdetect fallback")
            return

        try:
            # Mandate GPU for V2
            if self.device != "cuda":
                logger.warning("GPU not available for V2 Preprocessing. Falling back to Tier 3.")
                return

            logger.info("Loading Transformer LID V2 model (Tier 1 GPU)...")
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            model_name = "papluca/xlm-roberta-base-language-detection"
            
            # Try loading from cache first (offline mode)
            try:
                self._lid_tokenizer = AutoTokenizer.from_pretrained(model_name, local_files_only=True)
                self._lid_model = AutoModelForSequenceClassification.from_pretrained(
                    model_name, local_files_only=True
                ).to(self.device)
            except Exception:
                # Fallback to online download if not cached
                logger.info("Model not cached, downloading from HuggingFace...")
                self._lid_tokenizer = AutoTokenizer.from_pretrained(model_name)
                self._lid_model = AutoModelForSequenceClassification.from_pretrained(
                    model_name
                ).to(self.device)
            
            self._lid_model.eval()
            logger.info("Transformer LID V2 loaded successfully on GPU.")
        except Exception as e:
            logger.error(f"Failed to load Transformer LID V2: {e}")

    def warmup(self):
        """Warm up LID model"""
        logger.info("🔥 Warming up Preprocessing Service (LID)...")
        self._load_lid_v2()
        logger.info("✅ Preprocessing Service Warmup Complete")

    def _get_lid_model(self):
        self._load_lid_v2()
        return self._lid_model, self._lid_tokenizer

    # ----------------------------------------------------
    # Language detection
    # ----------------------------------------------------

    def detect_language(self, clean_text: str, raw_text: str = "") -> Dict[str, Any]:
        """
        Triple-Tier Language Detection (STRICT LOCAL GPU):
        1. Local V2 (Transformer classifier) GPU
        2. Cloud V2 (Trigger - TODO)
        3. Local V1 (langdetect) Safety Net
        """
        candidate = clean_text if len(clean_text.strip()) >= 12 else raw_text
        candidate = candidate.replace("\n", " ").strip()
        
        if not candidate:
            return {"value": "unknown", "confidence": 0.0, "role": "fallback"}

        # 🚀 FAST-PATH OPTIMIZATION:
        # Use langdetect for short text (< 50 chars) to avoid heavy Transformer model load latency.
        # Use high-accuracy Transformer model for long text (>= 50 chars).
        if len(candidate) < 50:
            logger.info(f"⚡ Using Fast-Path LID (langdetect) for short text ({len(candidate)} chars)")
            return self._detect_with_v1_langdetect(candidate)

        # --- TIER 1: Local V2 (Transformer GPU) ---
        logger.info(f"🧠 Using High-Accuracy LID (Transformer) for long text ({len(candidate)} chars)")
        lid_model, lid_tokenizer = self._get_lid_model()
        if lid_model and self.device == "cuda":
            try:
                inputs = lid_tokenizer(candidate, return_tensors="pt", truncation=True, max_length=128).to(self.device)
                with torch.no_grad():
                    outputs = lid_model(**inputs)
                    probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
                
                idx = torch.argmax(probs, dim=1).item()
                conf = float(probs[0][idx].item())
                lang = lid_model.config.id2label[idx]
                
                logger.debug(f"V2 GPU LID Detected: {lang} ({conf:.2f})")
                return {
                    "value": lang,
                    "confidence": conf,
                    "role": "primary"
                }
            except Exception as e:
                logger.error(f"Tier 1 GPU LID failed: {e}")
                # Fallback to Tier 3 if Tier 1 fails
                return self._detect_with_v1_langdetect(candidate)

        return self._detect_with_v1_langdetect(candidate)

    def _detect_with_v1_langdetect(self, candidate: str) -> Dict[str, Any]:
        """Internal helper for langdetect fallback"""
        # --- TIER 3: Local V1 (langdetect) ---
        try:
            # Use detect_langs() to get actual confidence scores
            from langdetect import detect_langs
            lang_probs = detect_langs(candidate)
            
            # Get the top result (highest confidence)
            if lang_probs:
                top_result = lang_probs[0]
                lang = top_result.lang
                conf = top_result.prob
                logger.debug(f"V1 langdetect Detected: {lang} (Confidence: {conf:.2f})")
                return {
                    "value": lang.split('-')[0], # Normalize to ISO-639-1 (e.g., en-US -> en)
                    "confidence": conf,
                    "role": "fallback"
                }
            else:
                logger.warning("Tier 3 (langdetect) returned no results")
                return {"value": "unknown", "confidence": 0.0, "role": "fallback"}
        except LangDetectException:
            logger.warning("Tier 3 (langdetect) failed due to insufficient text")
            return {"value": "unknown", "confidence": 0.0, "role": "fallback"}
        except Exception as e:
            logger.error(f"Tier 3 (langdetect) critical failure: {e}")
            return {"value": "unknown", "confidence": 0.0, "role": "fallback"}

    # ----------------------------------------------------
    # Cleaning (Unicode-safe)
    # ----------------------------------------------------

    def clean_text(self, text: str) -> str:
        # Type safety: Convert to string if needed
        if not isinstance(text, str):
            text = str(text) if text is not None else ""
        
        if not text or text.lower().strip() == "nan":
            return ""

        # 1️⃣ Unicode normalization (NFKC)
        text = unicodedata.normalize("NFKC", text)

        # 2️⃣ Fix Glued Content (Scraping/Syndication Noise)
        # Inject newlines if terminal punctuation is followed immediately by a character
        # Supports English (.), Hindi (।), and common terminators
        text = re.sub(r"([।\.!?])(?=[^\s\d])", r"\1\n\n", text)

        # 2️⃣ Punctuation Normalization (Smart quotes, dashes)
        for char, repl in self.punctuation_map.items():
            text = text.replace(char, repl)

        # 3️⃣ Remove Specific Artifacts (URLs, Tags, Junk)
        text = self.url_pattern.sub(" ", text)
        text = self.html_pattern.sub(" ", text)
        for pattern in self.junk_patterns:
            text = pattern.sub(" ", text)

        # 4️⃣ Emoji & Unicode Variation Selector Removal
        # VS16 (\uFE0F) and VS15 (\uFE0E) often remain after emoji removal
        text = self.emoji_pattern.sub(" ", text)
        text = re.sub(r"[\uFE00-\uFE0F\u200D]", "", text) # Strip variation selectors and ZWJ

        # 5️⃣ Balanced Whitespace Normalization
        # Collapse horizontal spaces to one (including all Unicode space categories)
        # Using [^\S\n\r] to target all horizontal whitespace
        text = re.sub(r"[^\S\r\n]+", " ", text)

        # Strip horizontal whitespace from each line individually
        # This ensures ZERO trailing spaces even on empty lines
        lines = [line.strip() for line in text.splitlines()]
        
        # Collapse 3+ newlines into 2 (preserve paragraphs)
        text = "\n".join(lines)
        text = re.sub(r"\n{3,}", "\n\n", text)
        
        # 6️⃣ Paragraph Deduplication (Exact Matches)
        # Useful for news syndication noise or scraping repetitions
        if "\n\n" in text:
            paragraphs = text.split("\n\n")
            unique_paragraphs = []
            seen_hashes = set()
            for p in paragraphs:
                p_clean = p.strip()
                if not p_clean: continue
                p_hash = hashlib.md5(p_clean.encode()).hexdigest()
                if p_hash not in seen_hashes:
                    unique_paragraphs.append(p)
                    seen_hashes.add(p_hash)
            text = "\n\n".join(unique_paragraphs)

        # Final document strip
        text = text.strip()

        logger.debug(f"Text cleaned: {len(text)} characters")
        return text

    # ----------------------------------------------------
    # Normalization (SAFE)
    # ----------------------------------------------------

    def normalize_text(self, text: str) -> str:
        """
        Normalization ONLY for hashing.
        DO NOT lowercase multilingual text.
        """
        # Type safety: Convert to string if needed
        if not isinstance(text, str):
            text = str(text) if text is not None else ""
        
        # Safety check for pandas NaN strings
        if text.lower().strip() == "nan":
            return ""
            
        if not text:
            return ""

        text = unicodedata.normalize("NFKC", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    # --- Integrated Logic Refinements (V19) ---
    def detect_mixed_script(self, text: str) -> bool:
        """Lightweight heuristic to detect if text contains multiple Unicode scripts"""
        if not text:
            return False
        try:
            # Get script names (e.g., 'LATIN', 'DEVANAGARI', 'HAN')
            scripts = set()
            for char in text:
                if char.isalpha():
                    name = unicodedata.name(char).split()[0]
                    scripts.add(name)
            return len(scripts) > 1
        except Exception:
            return False

    # ----------------------------------------------------
    # Segmentation (Translation-ready chunks)
    # ----------------------------------------------------

    def _get_segmenter(self, lang: str):
        """Lazy load pySBD segmenter for specific language"""
        # Normalize to base ISO code (e.g., en-US -> en, hi-IN -> hi)
        lang_iso = lang.split('-')[0].split('_')[0].lower()
        
        if lang_iso not in self._segmenters:
            try:
                import pysbd
                try:
                    # Attempt to load segmenter for the requested language
                    self._segmenters[lang_iso] = pysbd.Segmenter(language=lang_iso, clean=False)
                except (ValueError, KeyError):
                    # Fallback for unsupported languages (like 'kn') to 'en'
                    logger.warning(f"pySBD does not support '{lang_iso}', falling back to 'en'")
                    self._segmenters[lang_iso] = pysbd.Segmenter(language='en', clean=False)
            except Exception as e:
                logger.error(f"Failed to load pySBD segmenter for {lang_iso}: {e}")
                return None
        return self._segmenters.get(lang_iso)

    def segment_sentences(self, text: str, lang: str = "en") -> Dict[str, Any]:
        """
        Splits text into translation-ready sentence chunks (< 512 tokens).
        Returns Dict with 'segments' and 'metadata'.
        """
        if not text:
            return {"segments": [], "metadata": {"method": "none", "sentence_count": 0, "emergency_splits": 0}}

        method = "pysbd"
        oversized_splits = 0

        # 1. Primary: pySBD
        segmenter = self._get_segmenter(lang)
        if segmenter:
            try:
                segments = segmenter.segment(text)
            except Exception as e:
                logger.warning(f"pySBD segmentation failed: {e}. Falling back to regex.")
                method = "regex"
                segments = self._fallback_segmentation(text, lang)
        else:
            method = "regex"
            segments = self._fallback_segmentation(text, lang)

        # 2. Safety Check: Emergency split oversized sentences (> 1500 chars)
        final_segments = []
        for seg in segments:
            seg = seg.strip()
            if not seg:
                continue
            
            if len(seg) > 1500:
                oversized_splits += 1
                method = "emergency"
                parts = re.split(r"([,;।।。！？\s])", seg)
                current_part = ""
                for p in parts:
                    if len(current_part) + len(p) < 1000:
                        current_part += p
                    else:
                        final_segments.append(current_part.strip())
                        current_part = p
                if current_part:
                    final_segments.append(current_part.strip())
            else:
                final_segments.append(seg)

        return {
            "segments": [s for s in final_segments if s],
            "metadata": {
                "method": method,
                "used_pysbd": (segmenter is not None),
                "sentence_count": len(final_segments),
                "emergency_splits": oversized_splits
            }
        }

    def _fallback_segmentation(self, text: str, lang: str) -> list[str]:
        """Regex-based fallback for sentence splitting"""
        if lang == "hi":
            # Split by Danda (।) or Period
            return re.split(r"(?<=[।\.])\s+", text)
        elif lang == "zh":
            # Split by Chinese period, exclamation, or question
            return re.split(r"(?<=[。！？])\s*", text)
        else:
            # Standard English/General split
            return re.split(r"(?<=[.!?])\s+", text)

    # ----------------------------------------------------
    # Hashing
    # ----------------------------------------------------

    def compute_hash(self, text: str) -> str:
        if not text:
            return ""

        normalized = self.normalize_text(text)
        return hashlib.md5(normalized.encode("utf-8")).hexdigest()

    # ----------------------------------------------------
    # Pipeline entry
    # ----------------------------------------------------

    def preprocess(self, raw_text: str) -> Dict[str, Any]:
        try:
            clean_text = self.clean_text(raw_text)

            if clean_text == raw_text:
                logger.warning("Preprocessing produced no visible mutations")

            # Detect language (returns structured dict)
            lang_result = self.detect_language(clean_text, raw_text)

            text_hash = self.compute_hash(clean_text)

            # --- Integrated Logic Refinements (V19) ---
            is_mixed = self.detect_mixed_script(clean_text)
            seg_result = self.segment_sentences(clean_text, lang_result["value"])
            
            # --- 🚀 NEW: Enforce Quality Gate (CRITICAL) ---
            # 1. Length Factor (40% Weight): Over 500 chars = Max 0.4 points.
            cleaned_len = len(clean_text)
            len_weighted = min(cleaned_len / 500, 1.0) * 0.4
            
            # 2. Alpha Density Factor (60% Weight): Real content vs Junk.
            alnum_chars = [c for c in clean_text if c.isalnum() or ord(c) > 127]
            alnum_count = len(alnum_chars)
            alnum_ratio = alnum_count / max(1, cleaned_len)
            alpha_weighted = alnum_ratio * 0.6
            
            final_score = len_weighted + alpha_weighted
            threshold = 0.45
            passed = final_score >= threshold



            logger.info(
                f"Preprocessing complete - Passed: {passed} ({final_score:.4f}), "
                f"Lang: {lang_result['value']} (Mixed: {is_mixed}), "
                f"Sentences: {seg_result['metadata']['sentence_count']}, Hash: {text_hash[:8]}..."
            )

            return {
                "clean_text": clean_text,
                "language": lang_result,
                "is_mixed": is_mixed,
                "text_hash": text_hash,
                "sentences": seg_result["segments"],
                "segmentation": seg_result["metadata"],
                "quality_score": final_score,
                "passed": passed
            }

        except Exception as e:
            logger.error(f"Error in preprocessing pipeline: {e}")
            return {
                "clean_text": raw_text,
                "language": {"value": "unknown", "confidence": 0.0, "role": "fallback"},
                "text_hash": "",
                "sentences": [],
                "quality_score": 0.0,
                "passed": False
            }


# Singleton instance
preprocessing_service = PreprocessingService()

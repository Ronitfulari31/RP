"""
Translation Service
Handles automatic translation of non-English text to English
Tracks translation metadata and performance
"""

import logging
import time
import os
import threading
import re
from typing import Dict, Optional
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM


from app.services.core.preprocessing import preprocessing_service

# torch import moved to module level
TORCH_AVAILABLE = True 

logger = logging.getLogger(__name__)

# Silence verbose Argos loggers at module level - aggressive approach
for logger_name in ['argostranslate', 'argostranslate.utils', 'argostranslate.translate', 'stanza', 'huggingface_hub', 'transformers']:
    argos_logger = logging.getLogger(logger_name)
    argos_logger.setLevel(logging.ERROR)
    argos_logger.propagate = False
    argos_logger.handlers = []


SUPPORTED_TRANSLATION_CODES = {
    "af","sq","am","ar","hy","as","ay","az","bm","eu","be","bn","bho","bs","bg",
    "ca","ceb","ny","zh-CN","zh-TW","co","hr","cs","da","dv","doi","nl","en","eo",
    "et","ee","tl","fi","fr","fy","gl","ka","de","el","gn","gu","ht","ha","haw",
    "iw","hi","hmn","hu","is","ig","ilo","id","ga","it","ja","jw","kn","kk","km",
    "rw","gom","ko","kri","ku","ckb","ky","lo","la","lv","ln","lt","lg","lb","mk",
    "mai","mg","ms","ml","mt","mi","mr","mni-Mtei","lus","mn","my","ne","no","or",
    "om","ps","fa","pl","pt","pa","qu","ro","ru","sm","sa","gd","nso","sr","st",
    "sn","sd","si","sk","sl","so","es","su","sw","sv","tg","ta","tt","te","th",
    "ti","ts","tr","tk","ak","uk","ur","ug","uz","vi","cy","xh","yi","yo","zu"
}

LANGUAGE_CODE_MAP = {
    # Chinese (translator requires explicit variant)
    "zh": "zh-TW",
    "zh-cn": "zh-TW",
    "zh-tw": "zh-TW",

    # Hebrew legacy
    "he": "iw",

    # Indonesian legacy
    "in": "id",

    # Filipino naming mismatch
    "fil": "tl",

    # Norwegian variants
    "nb": "no",
    "nn": "no",

    # Kurdish variants
    "kur": "ku",

    # Serbian variants
    "sr-latn": "sr",

    # Portuguese variants
    "pt-br": "pt",
    "pt-pt": "pt",
}

# FLORES-200 Language Code Mapping for NLLB-200
NLLB_LANG_MAP = {
    "en": "eng_Latn",      # English
    "hi": "hin_Deva",      # Hindi
    "zh": "zho_Hans",      # Chinese (Simplified)
    "zh-CN": "zho_Hans",   # Chinese (Simplified)
    "zh-TW": "zho_Hant",   # Chinese (Traditional)
    "ar": "arb_Arab",      # Arabic
    "es": "spa_Latn",      # Spanish
    "fr": "fra_Latn",      # French
    "de": "deu_Latn",      # German
    "ja": "jpn_Jpan",      # Japanese
    "ko": "kor_Hang",      # Korean
    "ru": "rus_Cyrl",      # Russian
    "pt": "por_Latn",      # Portuguese
    "it": "ita_Latn",      # Italian
    "nl": "nld_Latn",      # Dutch
    "tr": "tur_Latn",      # Turkish
    "vi": "vie_Latn",      # Vietnamese
    "id": "ind_Latn",      # Indonesian
    "th": "tha_Thai",      # Thai
    "pl": "pol_Latn",      # Polish
    "bn": "ben_Beng",      # Bengali
    "ur": "urd_Arab",      # Urdu
    "ta": "tam_Taml",      # Tamil
    "te": "tel_Telu",      # Telugu
    "mr": "mar_Deva",      # Marathi
}


def should_skip_translation(text: str, source_lang: str) -> bool:
    """Stricter English check: Skip ONLY if source_lang is 'en' and text is pure ASCII"""
    if not text:
        return True
    if source_lang != "en":
        return False
    # Stricter: Only skip if zero non-ASCII characters
    non_ascii = sum(1 for c in text if ord(c) > 127)
    return non_ascii == 0

def token_loss_ratio(src: str, tgt: str) -> float:
    """
    Calculates ratio of 'anchor' tokens lost.
    Anchors are tokens that either:
    1. Exist in both source and target (Proprietary names, numbers)
    2. Are identified as critical entities.
    """
    if not src or not tgt:
        return 0.0
    
    # Extract 'Anchors' (Latin words, numbers) from source
    # These should definitely be preserved in the translation
    anchors = set(re.findall(r'\b[A-Za-z0-9]+\b', src))
    
    if not anchors:
        # If no Latin/numerical anchors, we use a simple proportion check
        # (Heuristic: Target length should be at least 40% of source for most langs)
        # But per user Fix 5, we'll return 0 if there's no shared set to check
        return 0.0
        
    tgt_tokens = set(re.findall(r'\b[A-Za-z0-9]+\b', tgt))
    intersection = len(anchors & tgt_tokens)
    return 1 - (intersection / len(anchors))


class TranslationService:
    """Service for text translation operations"""
    
    def __init__(self):
        self.translation_engine = "nllb-argos-hybrid" # Updated engine name
        self._argos_initialized = False
        self._unsupported_argos_paths = set()
        
        # Persistent Circuit Breakers (per session)
        self._google_circuit_broken = False
        self._last_google_failure = 0
        self._circuit_breaker_cooldown = 300  # 5 minutes
        
        # V2: NLLB-200 Models (GPU-accelerated)
        self.nllb_model_local = None
        self.nllb_tokenizer = None
        self.device = None
        self._nllb_failed = False  # Circuit breaker for failed NLLB loads
        self._load_lock = threading.Lock()

    def _init_argos(self):
        """Lazy-initialize Argos Translate (avoids startup delay)."""
        if self._argos_initialized:
            return True
        try:
            # Re-verify environment (Double-safety for Flask/multithreading)
            CACHE_BASE_PATH = os.getenv("CACHE_BASE_PATH", r"D:\Projects\Backend(SA)_cache")
            argos_cache = os.path.join(CACHE_BASE_PATH, "argos_cache", "packages")
            if os.environ.get("ARGOS_PACKAGES_DIR") != argos_cache:
                os.environ["ARGOS_PACKAGES_DIR"] = argos_cache
                argos_path = os.getenv("ARGOS_PACKAGES_DIR")
            
            # Pre-load NLLB and Argos in warmup
            self._load_nllb_v2()
            
            import argostranslate.package
            import argostranslate.translate
            self.argos = argostranslate.translate
            self._argos_initialized = True
            return True
        except ImportError:
            logger.info("================================================================")
            logger.warning("Argos Translate not installed — offline fallback disabled.")
            logger.info("================================================================")
            return False
        except Exception as e:
            logger.info("================================================================")
            logger.error(f"Failed to initialize Argos Translate: {e}")
            logger.info("================================================================")
            return False

    def init_argos(self):
        """
        Initialize Argos Translate using only locally installed packages.
        Skips internet calls to avoid timeouts.
        """
        if not self._init_argos():
            return
        try:
            import argostranslate.package
            
            # Skip internet call - just use what's already downloaded
            # argostranslate.package.update_package_index()
            
            # Get locally installed packages
            installed = argostranslate.package.get_installed_packages()
            logger.info("==========================================================")
            logger.info(f"Argos loaded {len(installed)} local language packages")
            logger.info("==========================================================")
        except Exception as e:
            logger.info("==========================================================")
            logger.error(f"Failed to fully initialize Argos: {e}")
            logger.info("==========================================================")

    def log_argos_languages(self):
        """Logs all installed Argos languages for debugging."""
        # Now uses the more robust init_argos logic
        self.init_argos()


    # ========================================================================
    # V2: NLLB-200 GPU-Accelerated Translation Methods
    # ========================================================================
    
    def _detect_gpu_v2(self):
        """Detect available GPU device for NLLB V2"""
        if self.device is None:
            if torch.cuda.is_available():
                self.device = "cuda"
                gpu_name = torch.cuda.get_device_name(0)
                logger.info(f"GPU detected for NLLB-200: {gpu_name}")
            else:
                self.device = "cpu"
                logger.warning("No GPU for NLLB-200, will use CPU")
        return self.device

    def _load_nllb_v2(self):
        """Load NLLB-200-distilled-600M for V2 translation"""
        with self._load_lock:
            if self.nllb_model_local is not None:
                return True
        
        if self._nllb_failed or not TORCH_AVAILABLE:
            return False
        
        try:
            logger.info("Loading NLLB-200-1.3B V2 (CUDA)...")
            
            model_name = "facebook/nllb-200-1.3B"
            cache_dir = os.getenv("TRANSFORMERS_CACHE", "D:/huggingface_cache")
            
            self.nllb_tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                cache_dir=cache_dir
            )
            
            device = self._detect_gpu_v2()
            self.device = device
            
            if device == "cuda":
                # Fix for meta tensor issue - load in CPU first, then move to GPU
                logger.info("Loading model to CPU first...")
                
                model = AutoModelForSeq2SeqLM.from_pretrained(
                    model_name,
                    cache_dir=cache_dir,
                    torch_dtype=torch.float32,  # Load in float32 on CPU
                    low_cpu_mem_usage=False     # Disable to avoid meta tensors
                )
                
                logger.info("Moving model to CUDA and converting to FP16...")
                # Move to CUDA and convert to half precision
                model = model.to("cuda").half().eval()
                
                self.nllb_model_local = model
                logger.info("Model successfully loaded on GPU in FP16")
            else:
                self.nllb_model_local = AutoModelForSeq2SeqLM.from_pretrained(
                    model_name,
                    cache_dir=cache_dir
                ).eval()
            
            logger.info("NLLB-200 V2 loaded successfully.")
            return True
            
        except Exception:
            logger.exception("Failed to load NLLB-200:")
            self.nllb_model_local = None
            self._nllb_failed = True
            return False

    def _normalize_lang_code_nllb(self, lang_code: str) -> str:
        """Convert ISO language code to FLORES-200 code for NLLB"""
        if not lang_code or lang_code == 'auto':
            return "eng_Latn"
        
        lang_code = lang_code.lower().strip()
        
        # Direct mapping
        if lang_code in NLLB_LANG_MAP:
            return NLLB_LANG_MAP[lang_code]
        
        # Try base language
        base = lang_code.split("-")[0]
        if base in NLLB_LANG_MAP:
            return NLLB_LANG_MAP[base]
        
        return "eng_Latn"

    def _translate_with_nllb_v2(self, input_data, source_lang: str, target_lang: str = "en", split_sentences: bool = True, translation_mode: str = "nlp"):
        """
        Translate using NLLB-200 V2 (Tier 1 - Primary).
        Supports Dual-Mode decoding:
        - 'nlp': Greedy decoding for token/entity stability.
        - 'display': Beam search for fluent English readability.
        
        Args:
            input_data: String or List of strings to translate.
            source_lang: ISO language code of source.
            target_lang: ISO language code of target.
            split_sentences: If True, splits single string into sentences for better accuracy.
            translation_mode: 'nlp' (greedy) or 'display' (beam).
        """
        if not self._load_nllb_v2():
            return None
        
        try:
            # Detect if input is already a batch
            is_batch = isinstance(input_data, list)
            
            # 🔹 Strategy: Optimized Batch Processing for Sentences
            # Stage 1 (Preprocessing) provides pre-segmented sentences (PREFERRED).
            # Fallback: If we receive raw text, we segment it here.
            
            if is_batch:
                # 🚀 Translation TRUSTS Stage 1 segmentation (Already a list)
                logger.debug(f"[NLLB] Processing Stage 1 batch: {len(input_data)} units")
                texts = input_data
            elif split_sentences:
                # 🚀 Fix: Handle long articles by splitting into sentences if not already batched
                # Use robust PreprocessingService for multilingual segmentation (Rule 8/10 Parity)
                seg_res = preprocessing_service.segment_sentences(input_data, lang=source_lang)
                texts = seg_res.get("segments", [input_data])
                logger.debug(f"[NLLB] Segmented string into {len(texts)} chunks using {seg_res.get('metadata', {}).get('method')}")
            else:
                # Single string fallback (e.g., Summaries or very short text)
                logger.debug(f"[NLLB] Single string mode (len: {len(input_data)})")
                texts = [input_data]
            
            if not texts:
                return [] if is_batch else ""
            
            # 🚀 BATCHING LOGIC (Max 8 sentences per forward pass)
            BATCH_SIZE = 8
            all_translations = []
            
            for i in range(0, len(texts), BATCH_SIZE):
                batch_texts = texts[i:i + BATCH_SIZE]
                
                # Filter empty strings
                valid_indices = [j for j, t in enumerate(batch_texts) if t and t.strip()]
                valid_texts = [batch_texts[j] for j in valid_indices]
                
                if not valid_texts:
                    all_translations.extend([""] * len(batch_texts))
                    continue

                src_code = self._normalize_lang_code_nllb(source_lang)
                tgt_code = self._normalize_lang_code_nllb(target_lang)
                
                with self._load_lock:
                    self.nllb_tokenizer.src_lang = src_code
                    tokens_params = self.nllb_tokenizer(
                        valid_texts,
                        return_tensors="pt",
                        max_length=512,
                        truncation=True,
                        padding=True 
                    ).to(self.device)
                    
                    forced_bos_token_id = self.nllb_tokenizer.convert_tokens_to_ids(tgt_code)

                # 🚀 DUAL-MODE DECODING STRATEGY (OPTIMIZED FOR SPEED)
                if translation_mode == "nlp":
                    # Greedy Decoding: No rephrasing, no compression, just literal mapping.
                    gen_params = {
                        "num_beams": 1,
                        "do_sample": False,
                        "length_penalty": 1.0,
                        "repetition_penalty": 1.1, # Reduced for stability in greedy mode
                        "no_repeat_ngram_size": 4,
                        "early_stopping": False
                    }
                elif translation_mode == "display":
                    # Fast Beam: Minimal beams for balance of quality and speed
                    gen_params = {
                        "num_beams": 1, # Switched to 1 for maximum pipeline throughput
                        "do_sample": False,
                        "length_penalty": 1.15,
                        "repetition_penalty": 1.2,
                        "no_repeat_ngram_size": 4,
                        "early_stopping": False
                    }
                else:
                    raise ValueError(f"Invalid translation_mode: {translation_mode}")

                # 🚀 OPTIMIZATION: Release lock during actual GPU generation
                # This prevents blocking other threads (like the API/UI) while worker is busy.
                translated_tokens = self.nllb_model_local.generate(
                    **tokens_params,
                    forced_bos_token_id=forced_bos_token_id,
                    max_new_tokens=448,
                    **gen_params
                )
                
                decoded_batch = self.nllb_tokenizer.batch_decode(
                    translated_tokens,
                    skip_special_tokens=True
                )
                
                # Reconstruct batch with empty strings
                batch_results = [""] * len(batch_texts)
                for idx_in_batch, pred in zip(valid_indices, decoded_batch):
                    batch_results[idx_in_batch] = pred
                
                all_translations.extend(batch_results)

            # 🚀 FIX 3: Preserve Sentence Alignment
            if is_batch and len(all_translations) != len(texts):
                logger.error(f"[TRANS] Sentence misalignment! Original: {len(texts)}, Translated: {len(all_translations)}")
                # Handled by flagging in higher-level nodes if possible

            # 🚀 Reassembly: Preserve paragraph/logical separation with \n
            if is_batch:
                return all_translations
            else:
                return "\n".join(all_translations)
            
        except Exception as e:
            # Check for CUDA Out of Memory (OOM)
            error_msg = str(e).lower()
            if "out of memory" in error_msg or "cuda error" in error_msg:
                logger.warning(f"[VRAM_ALERT] CUDA OOM. Clearing Cache and Retrying NOW...")
                
                # 🛠️ HARD-CORE TACKLING: Clear cache and force garbage collection
                import gc
                torch.cuda.empty_cache()
                gc.collect()
                
                try:
                    logger.info(f"[VRAM_RECOVERY] Retrying with Greedy Search (beams=1) to save memory.")
                    return self._translate_with_nllb_v2(input_data, source_lang, target_lang, split_sentences, translation_mode="nlp")
                except Exception as retry_e:
                    logger.error(f"[VRAM_FAIL] Retry also failed: {retry_e}")
            
            logger.exception("NLLB V2 translation failed:")
            return None

    def warmup(self):
        """Warm up NLLB-200 and Argos Translate"""
        logger.info("🔥 Warming up Translation Service (NLLB + Argos)...")
        self._load_nllb_v2()
        self.init_argos()
        logger.info("✅ Translation Service Warmup Complete")

    # ========================================================================
    # End of V2 Methods
    # ========================================================================

    def _resolve_argos_language(self, code: str):
        """
        Robust Argos language resolver.
        Handles cases like:
        hi  -> hi_IN
        zh  -> zh_CN / zh_TW
        id  -> id_ID
        ar  -> ar_SA
        """
        if not code or not self._init_argos():
            return None

        code = code.lower()
        langs = self.argos.get_installed_languages()

        # 1. Exact match (best case)
        for lang in langs:
            if lang.code.lower() == code:
                return lang

        # 2. Flexible Prefix match (hi -> hi_IN, zh-TW -> zh)
        for lang in langs:
            lc = lang.code.lower()
            # If engine code starts with input code (e.g., hi_IN starts with hi)
            # OR if input code starts with engine code (e.g., zh-TW starts with zh)
            if lc.startswith(code) or code.startswith(lc):
                return lang

        # 3. Known aliases (extra safety)
        aliases = {
            "hi": ["hi_in", "hin"],
            "zh": ["zh_cn", "zh_tw"],
            "zh-cn": ["zh"],
            "id": ["id_id"],
            "ar": ["ar_sa"],
            "fr": ["fr_fr"],
            "es": ["es_es"],
            "nl": ["nl_nl"],
        }

        for alias in aliases.get(code, []):
            for lang in langs:
                if lang.code.lower() == alias:
                    return lang

        # 4. Aggressive fallback: Language Name match (User requested)
        for lang in langs:
            name_lower = lang.name.lower()
            if code == "hi" and "hindi" in name_lower:
                return lang
            if code == "id" and "indonesian" in name_lower:
                return lang
            if code == "zh" and "chinese" in name_lower:
                return lang
            if code == "ar" and "arabic" in name_lower:
                return lang
            if code == "fr" and "french" in name_lower:
                return lang
            if code == "es" and "spanish" in name_lower:
                return lang

        all_codes = [f"{l.code} ({l.name})" for l in langs]
        logger.info("==========================================================")
        logger.error(f"[ARGOS] Unable to resolve language code: {code} | Installed: {all_codes}")
        logger.info("==========================================================")
        return None

    def _translate_with_argos(self, text: str, source_lang: str, target_lang: str, silent: bool = False):
        """Performs local translation using Argos with robust resolution."""
        if not self._init_argos():
            return None
            
        path_key = f"{source_lang}->{target_lang}"
        if path_key in self._unsupported_argos_paths:
            return None

        try:
            if not silent:
                logger.info("==========================================================")
                logger.info(
                    f"[ARGOS] Attempting translation | source={source_lang} target={target_lang}"
                )
                logger.info("==========================================================")

            from_lang = self._resolve_argos_language(source_lang)
            to_lang = self._resolve_argos_language(target_lang)

            if not from_lang or not to_lang:
                if path_key not in self._unsupported_argos_paths:
                    logger.info("==========================================================")
                    logger.error(
                        f"[ARGOS] Language resolution failed | from={source_lang} to={target_lang}"
                    )
                    logger.info("==========================================================")
                    self._unsupported_argos_paths.add(path_key)
                return None

            translation = from_lang.get_translation(to_lang)

            if not translation:
                if path_key not in self._unsupported_argos_paths:
                    logger.info("==========================================================")
                    logger.error(
                        f"[ARGOS] No translation path | from={from_lang.code} to={to_lang.code}"
                    )
                    logger.info("==========================================================")
                    self._unsupported_argos_paths.add(path_key)
                return None

            return translation.translate(text)

        except Exception as e:
            logger.info("==========================================================")
            if not silent:
                logger.exception(f"[ARGOS] Translation exception: {e}")
            logger.info("==========================================================")
            return None
    
    def normalize_for_translation(self, lang: str) -> str:
        """
        Converts stored language codes (zh, mr, es, etc.)
        into translation-engine-compatible codes.
        """
        if not lang or lang == "unknown":
            return "en"

        lang = lang.lower()

        # Step 1: explicit remap if needed
        mapped = LANGUAGE_CODE_MAP.get(lang, lang)

        # Step 2: if translator supports it -> done
        if mapped in SUPPORTED_TRANSLATION_CODES:
            return mapped

        # Step 3: try base language (e.g. zh-hans -> zh)
        base = mapped.split("-")[0]
        if base in SUPPORTED_TRANSLATION_CODES:
            return base

        # Step 4: last-resort safe fallback
        return "en"

    def _chunk_text(self, text: str, max_len: int = 4000) -> list[str]:
        """Splits text into chunks of max_len characters."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + max_len
            chunks.append(text[start:end])
            start = end
        return chunks

    def _split_sentences(self, text: str) -> list[str]:
        """
        Splits text into sentences using simple regex.
        Safe for most languages as it looks for common terminators followed by space.
        """
        if not text:
            return []
        # Split on . ! ? followed by whitespace, keeping the terminators
        # This is a robust enough heuristic for English->X translation tasks
        sentence_ends = re.compile(r'(?<=[.!?])\s+')
        sentences = sentence_ends.split(text.strip())
        return [s.strip() for s in sentences if s.strip()]

    def _translate_with_retry(self, translator, text):
        """Attempts translation ONCE. No retries to ensure zero latency on failure."""
        try:
            result = translator.translate(text)
            if result:
                return result
            return None
        except Exception as e:
            logger.info("==========================================================")
            logger.debug(f"Quick Google check failed: {e}")
            logger.info("==========================================================")
            return None

    def translate_text(self, text: str, target_lang: str, source_lang: str = "en", translation_mode: str = "display") -> str:
        """
        Generic translation method for any source/target pair (Standalone API).
        Default mode: 'display' (Prioritize human readability).
        """
        if not text or source_lang == target_lang:
            return text

        start_time = time.time()
        try:
            # 1. Clean and normalize text before translation (DAG Logic Parity)
            text = preprocessing_service.clean_text(text)
            if not text:
                return ""

            # 2. Normalize languages early
            clean_target = self.normalize_for_translation(target_lang)
            clean_source = self.normalize_for_translation(source_lang)
            
            # Optimization: Check AGAIN after normalization
            if clean_source == clean_target:
                logger.debug(f"[STANDALONE] Skipping translation (Normalized {clean_source} == {clean_target})")
                return text

            logger.info("==========================================================")
            logger.info(f"[STANDALONE] Starting translation: {clean_source} -> {clean_target}")
            logger.info("==========================================================")

            # ===================================================================
            # TIER 1: NLLB-200 V2 (GPU)
            # ===================================================================
            if TORCH_AVAILABLE and not self._nllb_failed:
                logger.info(f"[STANDALONE] Attempting NLLB-200 V2 ({translation_mode}) translation ({clean_source} -> {clean_target})...")
                nllb_result = self._translate_with_nllb_v2(text, clean_source, clean_target, translation_mode=translation_mode)
                if nllb_result and nllb_result.strip():
                    elapsed = time.time() - start_time
                    logger.info(f"[STANDALONE] NLLB-200 V2 {translation_mode} success ({elapsed:.3f}s)")
                    return nllb_result

            # ===================================================================
            # TIER 2: Argos (Offline) - Strictly aligned with pipeline
            # ===================================================================
            logger.info(f"[STANDALONE] Tier 2: Attempting Argos translation ({clean_source} -> {clean_target})...")
            translated = self._translate_with_argos(text, clean_source, clean_target)

            elapsed = time.time() - start_time
            if translated and translated != "[Translation Failed]":
                logger.info(f"[STANDALONE] Argos success ({elapsed:.3f}s)")
                return translated
            
            logger.error(f"[STANDALONE] Translation FAILED ({elapsed:.3f}s)")
            return "[Translation Failed]"
            
        except Exception as e:
            logger.error(f"[STANDALONE] Generic translation failed: {e}")
            return "[Translation Failed]"

    # ===================================================================
    # RESTORED: Batch Translation (Strict Compliance + Vectorized Optimization)
    # ===================================================================
    def translate_batch(self, texts: list[str], target_lang: str, source_lang: str = "en", translation_mode: str = "nlp") -> list[str]:
        """
        Translates a list of strings using the compliant local models (NLLB/Argos).
        Optimized to use NLLB vectorization (batch processing) on GPU for massive speedup.
        """
        if not texts:
            return []

        # Optimization: Check for equality after normalization globally for the batch
        # (Assuming entire batch is same source, which is true for our use case)
        clean_target = self.normalize_for_translation(target_lang)
        clean_source = self.normalize_for_translation(source_lang)
        
        if clean_source == clean_target:
             logger.debug(f"[BATCH] Skipping translation (Normalized {clean_source} == {clean_target})")
             return texts

        # TIER 1: NLLB Vectorized Batch
        if TORCH_AVAILABLE and not self._nllb_failed:
            logger.info(f"[BATCH] Attempting NLLB-200 V2 Vectorized Batch ({clean_source} -> {clean_target}) | Count: {len(texts)}")
            try:
                start_batch = time.time()
                results = self._translate_with_nllb_v2(texts, clean_source, clean_target, translation_mode=translation_mode)
                if results and len(results) == len(texts):
                    elapsed = time.time() - start_batch
                    logger.info(f"[BATCH] NLLB Vectorized Success ({elapsed:.3f}s)")
                    return results
            except Exception as e:
                logger.error(f"[BATCH] NLLB failed, falling back to iterative: {e}")

        # TIER 2: Iterative Fallback (Argos/Other)
        logger.info("[BATCH] Falling back to iterative translation...")
        results = []
        for text in texts:
            # We use the existing translate_text which handles NLLB -> Argos fallback
            translated = self.translate_text(text, target_lang, source_lang, translation_mode=translation_mode)
            
            # Handle failure case gracefully
            if translated == "[Translation Failed]":
                results.append(text) # Fallback to original
            else:
                results.append(translated)
        return results


    def translate_to_english(self, text: str = None, source_language: str = 'auto', sentences: list = None, translation_mode: str = "nlp") -> Dict:
        """
        Translate text to English (with automatic chunking and retries)
        
        Args:
            text: Full raw/cleaned text string
            source_language: Source language code
            sentences: Pre-segmented sentences from stage 1 (PREFERRED)
            translation_mode: 'nlp' (literal) or 'display' (fluent)
        """
        start_time = time.time()
        
        # Don't normalize 'auto' - let Google Translate handle auto-detection
        if source_language != 'auto':
            source_language = self.normalize_for_translation(source_language)
        
        try:
            # If sentences are provided, use them; otherwise use text
            if sentences is not None:
                if not sentences:
                    logger.warning("[TRANS] Skipping - No sentences provided.")
                    return {
                        'translated_text': "",
                        'original_language': source_language,
                        'translation_engine': self.translation_engine,
                        'success': True,
                        'skipped': True,
                        'reason': 'no_sentences'
                    }
                input_is_sentences = True
                texts_to_translate = sentences
                # For logging sample
                sample_text = sentences[0] if sentences else ""
            else:
                input_is_sentences = False
                # Ensure text is cleaned if it hasn't been already (for standalone API use)
                texts_to_translate = preprocessing_service.clean_text(text) if text else ""
                sample_text = texts_to_translate if texts_to_translate else ""

            # If text/sentences are missing or empty, skip
            if not texts_to_translate or (isinstance(texts_to_translate, str) and not texts_to_translate.strip()):
                return {
                    'translated_text': text if text else "",
                    'original_language': source_language,
                    'translation_engine': self.translation_engine,
                    'translation_time': 0.0,
                    'success': True,
                    'skipped': True
                }
            
            # 🚀 FIX 3: Stricter English check (ASCII Only)
            if should_skip_translation(texts_to_translate if not input_is_sentences else " ".join(texts_to_translate), source_language):
                logger.info("[TRANS] Text identified as English (ASCII), skipping translation.")
                return {
                    'translated_text': text if not input_is_sentences else " ".join(sentences),
                    'original_language': 'en',
                    'translation_engine': self.translation_engine,
                    'translation_time': 0.0,
                    'success': True,
                    'skipped': True,
                    'integrity': {'token_preservation': 1.0, 'alignment': 'ok'}
                }
            
            # Step 1: Resolve the source language once
            source_to_use = source_language
            
            # CRITICAL: If sentences provided, NEVER run langdetect (reuse Stage 1 metadata)
            if source_language == 'auto' and not input_is_sentences:
                try:
                    from langdetect import detect
                    detected_language = detect(sample_text[:500])
                    source_to_use = self.normalize_for_translation(detected_language)
                    logger.info(f"Auto-detected & Normalized: {source_to_use}")
                except Exception as e:
                    logger.warning(f"Language detection failed: {e}, using 'auto'")
                    source_to_use = 'auto'
            
            # Step 0 (moved after language detection): Priority 4 - Reduce Latency via early sentence chunking if not pre-provided
            if not input_is_sentences and len(texts_to_translate) > 350:
                seg_res = preprocessing_service.segment_sentences(texts_to_translate, lang=source_to_use)
                if seg_res.get("segments") and len(seg_res["segments"]) > 1:
                    logger.debug(f"[TRANS] Priority 4: Splitting long text into {len(seg_res['segments'])} segments")
                    texts_to_translate = seg_res["segments"]
                    input_is_sentences = True
            
            # ===================================================================
            # TIER 1: Try NLLB-200 V2 (GPU-Accelerated) FIRST
            # ===================================================================
            if source_to_use != 'auto' and TORCH_AVAILABLE:
                logger.info(f"Attempting {translation_mode} NLLB-200 V2 translation ({source_to_use} -> en)...")
                nllb_result = self._translate_with_nllb_v2(texts_to_translate, source_to_use, 'en', translation_mode=translation_mode)
                
                if nllb_result:
                    final_text = "\n".join(nllb_result) if isinstance(nllb_result, list) else nllb_result
                    src_flat = texts_to_translate if isinstance(texts_to_translate, str) else " ".join(texts_to_translate)
                    
                    # 🚀 Integrity & Safety Checks
                    coverage = 1 - token_loss_ratio(src_flat, final_text)
                    length_ratio = len(final_text) / max(1, len(src_flat))
                    
                    # Log fidelity
                    logger.info(f"[TRANS] Literal Fidelity: {coverage:.1%} coverage, {length_ratio:.1%} length ratio")
                    
                    translation_time = time.time() - start_time
                    
                    # Quality Scoring Logic
                    if coverage >= 0.85: q_score = 1.0
                    elif coverage >= 0.70: q_score = 0.8
                    elif coverage >= 0.50: q_score = 0.4
                    else: q_score = 0.0
                    
                    return {
                        'translated_text': final_text,
                        'original_language': source_to_use,
                        'translation_engine': 'nllb-200-v2',
                        'translation_time': round(translation_time, 3),
                        'success': True,
                        'skipped': False,
                        'integrity': {
                            'token_coverage': round(coverage, 2),
                            'length_ratio': round(length_ratio, 2),
                            'quality_score': q_score,
                            'alignment': 'ok' if not isinstance(nllb_result, list) or len(nllb_result) == len(texts_to_translate) else 'mismatch',
                            'translation_mode': translation_mode
                        }
                    }
                else:
                    logger.warning("NLLB-200 V2 failed, falling back to Argos...")
            
            # ===================================================================
            # TIER 2: Argos Offline Fallback (Iterative)
            # ===================================================================
            logger.info(f"Tier 2: Attempting Argos translation ({source_to_use} -> en)...")
            
            # Chunking logic for long articles if we only have raw text
            if not input_is_sentences:
                work_texts = self._chunk_text(texts_to_translate, max_len=4000)
            else:
                work_texts = texts_to_translate
                
            translated_chunks = []
            any_chunk_failed = False
            
            for chunk in work_texts:
                argos_trans = self._translate_with_argos(chunk, source_to_use, "en", silent=True)
                if argos_trans:
                    translated_chunks.append(argos_trans)
                else:
                    translated_chunks.append("[Translation Failed]")
                    any_chunk_failed = True
            
            translated_text = " ".join(translated_chunks)
            translation_time = time.time() - start_time
            
            if not any_chunk_failed and translated_text and translated_text.strip():
                logger.info(f"Argos translation successful ({translation_time:.3f}s)")
                return {
                    'translated_text': translated_text,
                    'original_language': source_to_use,
                    'translation_engine': 'argostranslate',
                    'translation_time': round(translation_time, 3),
                    'success': True,
                    'skipped': False
                }
            
            # ===================================================================
            # All tiers failed - return original text
            # ===================================================================
            logger.error("All translation tiers failed (NLLB + Argos)")
            return {
                'translated_text': text,
                'original_language': source_to_use,
                'translation_engine': 'none',
                'translation_time': round(translation_time, 3),
                'success': False,
                'error': 'Translation failed',
                'skipped': False
            }

            
        except Exception as e:
            translation_time = time.time() - start_time
            logger.info("==========================================================")
            logger.error(f"Translation failed: {e}")
            logger.info("==========================================================")
            
            # Return original text if translation fails
            return {
                'translated_text': text,
                'original_language': source_language,
                'translation_engine': self.translation_engine,
                'translation_time': round(translation_time, 3),
                'success': False,
                'error': str(e),
                'skipped': False
            }
    
    def translate_multiple(self, texts: list, source_language: str = 'auto') -> list:
        """
        Translate multiple texts
        
        Args:
            texts: List of texts to translate
            source_language: Source language code
            
        Returns:
            List of translation result dictionaries
        """
        results = []
        
        for text in texts:
            result = self.translate_to_english(text, source_language)
            results.append(result)
        
        return results
    
    def get_supported_languages(self) -> Dict[str, str]:
        """
        Get list of supported languages
        
        Returns:
            Dictionary of language codes and names
        """
        # Common languages for disaster response
        return {
            'en': 'English',
            'hi': 'Hindi',
            'es': 'Spanish',
            'fr': 'French',
            'ar': 'Arabic',
            'zh-CN': 'Chinese (Simplified)',
            'ja': 'Japanese',
            'ko': 'Korean',
            'pt': 'Portuguese',
            'ru': 'Russian',
            'de': 'German',
            'it': 'Italian',
            'tr': 'Turkish',
            'vi': 'Vietnamese',
            'id': 'Indonesian',
            'th': 'Thai',
            'pl': 'Polish',
            'nl': 'Dutch',
            'bn': 'Bengali',
            'ur': 'Urdu',
            'ta': 'Tamil',
            'te': 'Telugu',
            'mr': 'Marathi'
        }


# Singleton instance
translation_service = TranslationService()

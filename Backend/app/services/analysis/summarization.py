import logging
import time
import os
import torch
import threading
from typing import Dict, Any, List
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

logger = logging.getLogger(__name__)


class SummarizationService:
    def __init__(self):
        # Tier 1: BART (Abstractive)
        self.bart_model = None
        self.bart_tokenizer = None
        self.bart_available = False
        self._bart_attempted = False
        self._load_lock = threading.Lock()
        
        # Hardware setup
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        if self.device != "cuda":
            logger.warning("🚨 GPU NOT DETECTED! Summarization V2 mandate requires GPU.")

    def _load_bart_v2(self):
        """Lazy load the BART-large-cnn V2 model (Tier 1 GPU)"""
        with self._load_lock:
            if self._bart_attempted:
                return
            self._bart_attempted = True

        try:
            logger.info("🔄 Loading BART-large V2 model (Tier 1 GPU)...")
            model_name = "facebook/bart-large-cnn"
            cache_dir = os.getenv("TRANSFORMERS_CACHE", "D:/huggingface_cache")
            
            if self.device != "cuda":
                raise RuntimeError("GPU not available for V2 Mandate")

            self.bart_tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                cache_dir=cache_dir
            )
            
            # Fix for meta tensor issue - load in CPU first, then move to GPU
            logger.info("🔧 Loading BART to CPU first...")
            self.bart_model = AutoModelForSeq2SeqLM.from_pretrained(
                model_name,
                cache_dir=cache_dir,
                torch_dtype=torch.float32,
                low_cpu_mem_usage=False
            )
            
            logger.info("🔧 Moving BART to CUDA and converting to FP16...")
            self.bart_model = self.bart_model.to(self.device).half().eval()
            
            self.bart_available = True
            logger.info("✅ BART-large V2 loaded successfully on GPU in FP16.")

        except Exception as e:
            logger.error(f"❌ Failed to load BART V2: {e}")
            self.bart_available = False

    def warmup(self):
        """Warm up BART model"""
        logger.info("🔥 Warming up Summarization Service (BART)...")
        self._load_bart_v2()
        logger.info("✅ Summarization Service Warmup Complete")

    def summarize_extractive_v1(self, text: str, sentences_count: int = 3) -> str:
        """TIER 3: Extractive (Sumy LSA) Fallback"""
        try:
            from sumy.parsers.plaintext import PlaintextParser
            from sumy.nlp.tokenizers import Tokenizer
            from sumy.summarizers.lsa import LsaSummarizer

            parser = PlaintextParser.from_string(text, Tokenizer("english"))
            summarizer = LsaSummarizer()

            summary_sentences = summarizer(parser.document, sentences_count)
            summary = " ".join(str(sentence) for sentence in summary_sentences)
            return summary.strip()
        except Exception as e:
            logger.error(f"Extractive V1 failed: {e}")
            return text[:500] + "..."

    def summarize_abstractive_v2(self, text: str) -> str | None:
        """TIER 1: Abstractive (BART-large) GPU-only"""
        try:
            self._load_bart_v2()
            if not self.bart_available:
                return None

            # BART prefers lengths around 512-1024; truncate if too long
            inputs = self.bart_tokenizer(
                text, 
                max_length=1024, 
                truncation=True, 
                return_tensors="pt"
            ).to(self.device)

            with torch.no_grad():
                summary_ids = self.bart_model.generate(
                    inputs["input_ids"],
                    num_beams=1, # 🚀 OPTIMIZED: Switched to Greedy Search for 4x speedup
                    min_length=30,
                    max_length=300,
                    early_stopping=True
                )

            summary = self.bart_tokenizer.decode(summary_ids[0], skip_special_tokens=True)
            return summary.strip()
        except Exception as e:
            logger.error(f"Tier 1 GPU (BART) failed: {e}")
            return None

    def summarize(self, text: str, method: str = "auto", sentences_count: int = 3) -> Dict[str, Any]:
        """
        Unified Summarization API with Triple-Tier GPU Logic
        """
        start_time = time.time()
        
        # Word count check
        word_count = len(text.split())
        
        # 🟢 FEEDBACK FIX: If text is short (< 40 words), don't fail or fallback.
        # Just return the original text as the summary since it's already readable.
        if not text or (word_count < 40 and len(text) < 300):
            logger.info(f"Short article ({word_count} words). Returning raw text as summary.")
            return {
                "value": text.strip(),
                "confidence": 1.0,
                "role": "raw_pass",
                "status": "RAW_TEXT_PERMITTED",
                "raw_scores": {"abstractive": "", "extractive": text},
                "analysis_time": 0.0
            }

        result_summary = None
        status = "auto_detect"
        role = "primary"
        raw_scores = {"abstractive": "", "extractive": ""}

        # RERUN LOGIC: If this is a user-triggered retry or second attempt
        is_retry = method == "retry_high_intensity"

        # --- Tier 1: Local V2 (BART Abstractive) ---
        if method in ["auto", "v2"] or is_retry:
            result_summary = self.summarize_abstractive_v2(text)
            if result_summary:
                status = "READY_FOR_LOCAL_GPU"
                role = "primary"
                raw_scores["abstractive"] = result_summary

        # --- Tier 2: Cloud V2 (Placeholder) ---
        if result_summary is None and method == "auto":
            logger.warning("Tier 1 Failed. Cloud V2 Trigger not yet active. Falling back to Tier 3.")

        # --- Tier 3: Local V1 (Sumy Extractive) ---
        if result_summary is None:
            result_summary = self.summarize_extractive_v1(text, sentences_count)
            status = "FALLBACK_TO_V1_GPU_SAFETY" # Technically CPU but designated safety tier
            role = "fallback"
            raw_scores["extractive"] = result_summary

        return {
            "value": result_summary,
            "confidence": 0.95 if role == "primary" else 0.7,
            "role": role,
            "status": status,
            "history": [],
            "raw_scores": raw_scores,
            "analysis_time": round(time.time() - start_time, 3)
        }


# Singleton instance
summarization_service = SummarizationService()

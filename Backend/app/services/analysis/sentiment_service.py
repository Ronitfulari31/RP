"""
Sentiment Analysis Service
Supports BERTweet (social media focused) with lazy loading
Handles multilingual sentiment analysis safely
"""

import logging
import time
import os
# torch import moved to local scope for performance
import threading
from typing import Dict, Any, Optional
# transformers imports moved to shared scope
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

logger = logging.getLogger(__name__)


class SentimentService:
    """Service for sentiment analysis operations"""

    def __init__(self):

        # Tier 1: RoBERTa-large (V2)
        self.roberta_v2_model = None
        self.roberta_v2_tokenizer = None
        self.roberta_v2_available = False
        self._roberta_v2_attempted = False

        # Tier 3: BERTweet (V1)
        self.bertweet_model = None
        self.bertweet_tokenizer = None
        self.bertweet_available = False
        self._bertweet_attempted = False
        
        self._load_lock = threading.Lock()
        
        # Hardware setup
        try:
            import torch
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            self.device = "cpu"
            
        if self.device != "cuda":
            logger.warning("GPU NOT DETECTED! NLP Pipeline V2 mandate requires GPU.")

    # ---------------------------------------------------------
    # Lazy BERTweet Loader
    # ---------------------------------------------------------
    def _load_roberta_v2(self):
        """Lazy load the RoBERTa-base V2 model (Tier 1 GPU)"""
        with self._load_lock:
            if self._roberta_v2_attempted:
                return
            self._roberta_v2_attempted = True

        try:
            logger.info("Loading RoBERTa-base V2 model (Tier 1 GPU)...")
            # Using latest CardiffNLP model which has full safetensors support
            model_name = "cardiffnlp/twitter-roberta-base-sentiment-latest" 
            
            if self.device != "cuda":
                raise RuntimeError("GPU not available for V2 Mandate")

            self.roberta_v2_tokenizer = AutoTokenizer.from_pretrained(model_name)
            
            logger.info("Loading RoBERTa to CPU first (bypassing meta tensors)...")
            model = AutoModelForSequenceClassification.from_pretrained(
                model_name,
                use_safetensors=True,
                torch_dtype=torch.float32,
                low_cpu_mem_usage=False
            )
            
            logger.info("Moving RoBERTa to CUDA and Quantizing to FP16...")
            self.roberta_v2_model = model.to(self.device).half().eval() 
            self.roberta_v2_available = True
            logger.info("RoBERTa V2 loaded successfully on GPU.")

        except Exception as e:
            logger.error(f"Failed to load RoBERTa V2: {e}")
            self.roberta_v2_available = False

    def _load_bertweet(self):
        """Lazy load the BERTweet V1 model (Tier 3)"""
        with self._load_lock:
            if self._bertweet_attempted:
                return
            self._bertweet_attempted = True

        try:
            logger.info("Loading BERTweet V1 model (Tier 3)...")
            model_name = "finiteautomata/bertweet-base-sentiment-analysis"
            
            if self.device != "cuda":
                raise RuntimeError("GPU not available for V1 Safety Net Mandate")

            self.bertweet_tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=False)
            
            logger.info("Loading BERTweet to CPU first (bypassing meta tensors)...")
            model = AutoModelForSequenceClassification.from_pretrained(
                model_name,
                use_safetensors=True,
                torch_dtype=torch.float32,
                low_cpu_mem_usage=False
            )
            
            logger.info("Moving BERTweet to CUDA and Quantizing to FP16...")
            self.bertweet_model = model.to(self.device).half().eval()
            self.bertweet_available = True
            logger.info("BERTweet V1 loaded successfully on GPU.")

        except Exception as e:
            logger.error(f"Failed to load BERTweet V1: {e}")
            self.bertweet_available = False

    def warmup(self):
        """Warm up RoBERTa and BERTweet models"""
        logger.info("🔥 Warming up Sentiment Service (RoBERTa + BERTweet)...")
        self._load_roberta_v2()
        self._load_bertweet()
        logger.info("✅ Sentiment Service Warmup Complete")

    # ---------------------------------------------------------
    # Sentiment Engines
    # ---------------------------------------------------------
    def analyze_with_v2_local(self, text: str) -> Dict | None:
        """TIER 1: Local V2 (RoBERTa-large) GPU-only"""
        try:
            self._load_roberta_v2()
            inputs = self.roberta_v2_tokenizer(
                text, return_tensors="pt", truncation=True, max_length=512
            ).to(self.device)

            with torch.no_grad():
                outputs = self.roberta_v2_model(**inputs)
                probs = torch.nn.functional.softmax(outputs.logits, dim=-1)

            idx = torch.argmax(probs, dim=1).item()
            confidence = probs[0][idx].item()

            # Mapping for CardiffNLP Latest: 0: negative, 1: neutral, 2: positive
            sentiment_map = {0: "negative", 1: "neutral", 2: "positive"}
            
            return {
                "value": sentiment_map.get(idx, "unknown"),
                "confidence": round(confidence, 4),
                "role": "primary",
                "raw_scores": {
                    "negative": round(probs[0][0].item(), 4),
                    "neutral": round(probs[0][1].item(), 4) if probs.size(1) > 1 else 0.0,
                    "positive": round(probs[0][2].item(), 4) if probs.size(1) > 2 else 0.0
                }
            }
        except Exception as e:
            logger.error(f"Tier 1 GPU (RoBERTa) failed: {e}")
            return None

    def analyze_with_v1_local(self, text: str) -> Dict | None:
        """TIER 3: Local V1 (BERTweet) GPU-only Safety Net"""
        try:
            self._load_bertweet()
            inputs = self.bertweet_tokenizer(
                text, return_tensors="pt", truncation=True, max_length=128
            ).to(self.device)

            with torch.no_grad():
                outputs = self.bertweet_model(**inputs)
                probs = torch.nn.functional.softmax(outputs.logits, dim=-1)

            idx = torch.argmax(probs, dim=1).item()
            confidence = probs[0][idx].item()

            sentiment_map = {0: "negative", 1: "neutral", 2: "positive"}

            return {
                "value": sentiment_map[idx],
                "confidence": round(confidence, 4),
                "role": "fallback",
                "raw_scores": {
                    "negative": round(probs[0][0].item(), 4),
                    "neutral": round(probs[0][1].item(), 4),
                    "positive": round(probs[0][2].item(), 4),
                },
            }
        except Exception as e:
            logger.error(f"Tier 3 GPU (BERTweet) failed: {e}")
            return None



    # ---------------------------------------------------------
    # Unified API (cleaned → summary → raw)
    # ---------------------------------------------------------
    def analyze(
        self,
        cleaned_text: str | None = None,
        summary_text: str | None = None,
        raw_text: str | None = None,
        method: str = "auto",
    ) -> Dict:
        """
        Unified Sentiment API with Triple-Tier GPU Logic:
        1. Local V2 (RoBERTa-large) GPU
        2. Cloud V2 (Trigger - TODO)
        3. Local V1 (BERTweet) GPU
        """
        start_time = time.time()

        # Selection logic: cleaned -> summary -> raw
        text = cleaned_text or summary_text or raw_text
        if not text:
            return {
                "value": "neutral",
                "confidence": 0.0,
                "role": "fallback",
                "status": "skipped_no_text",
                "history": [],
                "analysis_time": 0.0
            }

        result = None

        # --- Tier 1: Local V2 GPU ---
        if method in ["auto", "v2"]:
            # Check for memory safety/VRAM before trying (TODO: Add VRAM check logic)
            # Try Local V2
            result = self.analyze_with_v2_local(text)
            if result:
                result["status"] = "READY_FOR_LOCAL_GPU"

        # --- Tier 2: Cloud V2 (Placeholder for Trigger) ---
        if result is None and method == "auto":
            # This is where we will trigger the Kaggle CLI in future phases
            # For now, we move straight to Tier 3 fallback
            logger.warning("Tier 1 Failed. Cloud V2 Trigger not yet active. Falling back to Tier 3.")

        # --- Tier 3: Local V1 GPU Safety Net ---
        if result is None:
            result = self.analyze_with_v1_local(text)
            if result:
                result["status"] = "FALLBACK_TO_V1_GPU_SAFETY"

        # If everything failed
        if result is None:
            result = {
                "value": "neutral",
                "confidence": 0.0,
                "role": "fallback",
                "status": "total_failure",
                "raw_scores": {}
            }

        result["analysis_time"] = round(time.time() - start_time, 3)
        result["history"] = [] # Placeholder for future history tracking

        logger.info(
            f"Sentiment Result: {result['value']} ({result['confidence']}) "
            f"via {result['status']} (Role: {result['role']})"
        )

        return result


# Singleton accessor
# ------------------------------------------------------------------
_sentiment_service_instance = None


def get_sentiment_service() -> SentimentService:
    global _sentiment_service_instance

    if _sentiment_service_instance is None:
        logger.info("Creating SentimentService singleton")
        _sentiment_service_instance = SentimentService()

    return _sentiment_service_instance

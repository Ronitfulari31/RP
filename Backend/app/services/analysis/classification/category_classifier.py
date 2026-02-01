import re
import logging
import time
import os
from typing import Dict, List, Optional
import torch
import threading

logger = logging.getLogger(__name__)

# -------------------------
# Category Keyword Map (Tier 3 Fallback)
# -------------------------
CATEGORY_KEYWORDS = {
    "sports": [
        "match", "tournament", "league", "goal", "score", "cricket", "football",
        "soccer", "tennis", "badminton", "olympics", "world cup", "player", "coach"
    ],
    "entertainment": [
        "film", "movie", "cinema", "actor", "actress", "bollywood", "hollywood",
        "music", "song", "album", "trailer", "web series", "netflix", "ott"
    ],
    "business": [
        "market", "stock", "shares", "investment", "revenue", "profit", "loss",
        "startup", "funding", "ipo", "company", "corporate", "economy", "trade"
    ],
    "politics": [
        "government", "election", "minister", "parliament", "policy", "law",
        "president", "prime minister", "bjp", "congress", "senate", "vote"
    ],
    "disaster": [
        "earthquake", "flood", "cyclone", "hurricane", "wildfire", "landslide",
        "tsunami", "drought", "storm", "emergency", "rescue", "evacuation"
    ],
    "terror_attack": [
        "terror", "terrorist", "attack", "bomb", "blast", "explosion",
        "suicide bombing", "militant", "gunmen", "hostage", "isis", "al-qaeda"
    ],
    "infrastructure": [
        "road", "highway", "bridge", "railway", "train", "airport", "port",
        "construction", "building", "transport", "metro", "power grid", "dam"
    ]
}

# -------------------------
# V2 State Management
# -------------------------
_classifier_pipeline = None
_load_failed = False
_device = "cpu"
_load_lock = threading.Lock()

def _detect_gpu():
    """Detect best available GPU."""
    if torch.cuda.is_available():
        try:
            device_name = torch.cuda.get_device_name(0)
            logger.info(f"GPU detected for Classification: {device_name}")
            return "cuda"
        except Exception:
            pass
    return "cpu"

def _load_transformer_v2():
    """Load BART Zero-Shot model using CPU-first strategy."""
    global _classifier_pipeline, _load_failed, _device
    
    with _load_lock:
        if _classifier_pipeline is not None:
            return True
        if _load_failed:
            return False
        
    try:
        from transformers import pipeline, AutoModelForSequenceClassification, AutoTokenizer
        
        model_name = "facebook/bart-large-mnli"
        cache_dir = os.getenv("TRANSFORMERS_CACHE", "D:/huggingface_cache")
        _device = _detect_gpu()
        
        if _device == "cuda":
            logger.info(f"Loading {model_name} V2 (Tier 1 GPU)...")
            
            # CPU-first strategy to bypass meta tensor issues
            model = AutoModelForSequenceClassification.from_pretrained(
                model_name,
                cache_dir=cache_dir,
                torch_dtype=torch.float32,
                low_cpu_mem_usage=False
            )
            tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=cache_dir)
            
            logger.info("Moving model to CUDA and Quantizing to FP16...")
            model = model.to("cuda").half().eval()
            
            _classifier_pipeline = pipeline(
                "zero-shot-classification",
                model=model,
                tokenizer=tokenizer
            )
        else:
            logger.info(f"Loading {model_name} V2 (CPU Fallback)...")
            _classifier_pipeline = pipeline(
                "zero-shot-classification",
                model=model_name,
                cache_dir=cache_dir
            )
            
        logger.info(f"Topic Classification V2 loaded successfully on {_device}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to load Classification V2: {e}")
        _load_failed = True
        return False

def warmup():
    """Warm up Category Classification model"""
    logger.info("🔥 Warming up Category Classification (BART)...")
    _load_transformer_v2()
    logger.info("✅ Category Classification Warmup Complete")

# -------------------------
# Classifier Function
# -------------------------
def classify_category(text: str, min_confidence: float = 0.15) -> Dict:
    """
    Classify text into news categories using Triple-Tier logic.
    """
    start_time = time.time()
    
    # Tier 1/2: NLI-based Zero-Shot
    if not _load_failed and _load_transformer_v2():
        try:
            # BART-Large is heavy, truncate for performance
            input_text = text[:1024]
            candidate_labels = list(CATEGORY_KEYWORDS.keys())
            
            result = _classifier_pipeline(
                input_text,
                candidate_labels=candidate_labels,
                multi_label=False
            )
            
            primary = result['labels'][0]
            confidence = round(result['scores'][0], 3)
            
            if confidence > 0.35:
                analysis_time = round(time.time() - start_time, 3)
                logger.info(f"Classification successful: {primary} ({confidence}) - {analysis_time}s")
                
                return {
                    "primary": primary,
                    "confidence": confidence,
                    "labels": [{"label": l, "confidence": round(s, 3)} for l, s in zip(result['labels'], result['scores'])],
                    "method": f"bart-v2-{_device}",
                    "analysis_time": analysis_time
                }
        except Exception as e:
            logger.error(f"Zero-shot classification failed: {e}")

    # Tier 3: Keyword Fallback (Original Logic)
    try:
        if not text or not isinstance(text, str):
            return {"primary": "unknown", "confidence": 0.0, "labels": []}

        clean_text = text.lower()
        scores = {}

        for category, keywords in CATEGORY_KEYWORDS.items():
            count = 0
            for kw in keywords:
                if re.search(rf"\b{re.escape(kw)}\b", clean_text):
                    count += 1
            if count > 0:
                scores[category] = count

        if not scores:
            return {"primary": "unknown", "confidence": 0.0, "labels": [], "method": "keyword"}

        total_hits = sum(scores.values())
        labels = []
        for cat, hits in scores.items():
            conf = round(hits / total_hits, 2)
            if conf >= min_confidence:
                labels.append({"label": cat, "confidence": conf})

        labels.sort(key=lambda x: x["confidence"], reverse=True)

        if not labels:
            return {"primary": "unknown", "confidence": 0.0, "labels": [], "method": "keyword"}

        return {
            "primary": labels[0]["label"],
            "confidence": labels[0]["confidence"],
            "labels": labels,
            "method": "keyword",
            "analysis_time": round(time.time() - start_time, 3)
        }

    except Exception as e:
        logger.error(f"[category_classifier] Keyword fallback failed: {e}")
        return {"primary": "unknown", "confidence": 0.0, "labels": [], "method": "error"}

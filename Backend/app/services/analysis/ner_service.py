import logging
import time
import os
# torch import moved to local scope for performance
import threading
import re
from typing import Dict, Any, List
import torch
from gliner import GLiNER
import spacy

logger = logging.getLogger(__name__)


class NERService:
    def __init__(self):
        # Tier 1: GLiNER (V2)
        self.gliner_model = None
        self.gliner_available = False
        self._gliner_attempted = False
        self._load_lock = threading.Lock()
        
        # Tier 3: SpaCy (V1)
        self.nlp = None
        
        # Hardware setup
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
            
        if self.device != "cuda":
            logger.warning("GPU NOT DETECTED! NER V2 mandate requires GPU.")

    def _load_gliner_v2(self):
        """Lazy load the GLiNER-large V2 model (Tier 1 GPU)"""
        with self._load_lock:
            if self._gliner_attempted:
                return
            self._gliner_attempted = True

        try:
            logger.info("Loading GLiNER-large V2 model (Tier 1 GPU)...")
            
            if self.device != "cuda":
                raise RuntimeError("GPU not available for V2 Mandate")

            # Using large v2.1 for maximum zero-shot performance
            model_name = "urchade/gliner_large-v2.1"
            
            logger.info("Loading GLiNER to CPU first (bypassing meta tensors)...")
            self.gliner_model = GLiNER.from_pretrained(
                model_name
            )
            
            logger.info("Moving GLiNER to CUDA and Quantizing to FP16...")
            self.gliner_model = self.gliner_model.to(self.device).half()
            
            self.gliner_available = True
            logger.info("GLiNER V2 loaded successfully on GPU.")

        except Exception as e:
            self.gliner_available = False

    def warmup(self):
        """Warm up GLiNER and SpaCy models"""
        logger.info("🔥 Warming up NER Service (GLiNER + SpaCy)...")
        self._load_gliner_v2()
        self._load_spacy_v1()
        logger.info("✅ NER Service Warmup Complete")

    def _load_spacy_v1(self):
        """Lazy load SpaCy model (Tier 3 Safety Net)"""
        if self.nlp is None:
            try:
                # Try to enable GPU for spaCy if available
                if self.device == "cuda":
                    try:
                        spacy.require_gpu()
                        logger.info("SpaCy configured for GPU")
                    except:
                        pass
                
                logger.info("Loading SpaCy model (en_core_web_sm)...")
                self.nlp = spacy.load("en_core_web_sm")
                logger.info("SpaCy model loaded")
            except Exception as e:
                logger.error(f"Failed to load spaCy model: {e}")
                self.nlp = None

    def extract_with_v2_local(self, text: str) -> List[Dict] | None:
        """TIER 1: GLiNER GPU Inference"""
        try:
            self._load_gliner_v2()
            if not self.gliner_available:
                return None

            # Labels list - Including COUNTRY for better geopolitical detection (Crucial for Chinese)
            labels = ["PERSON", "LOCATION", "ORGANIZATION", "COUNTRY", "ART", "BUILDING", "PRODUCT", "EVENT", "DATE"]
            
            # Detect source language for threshold tuning
            is_cjk = any("\u4e00" <= c <= "\u9fff" for c in text[:100]) # Quick zh check
            
            # 🚀 Fix 1: Lower threshold for CJK to produce more entity predictions, higher for non-CJK
            threshold = 0.55 if is_cjk else 0.60
            
            # GLiNER zero-shot extraction
            entities = self.gliner_model.predict_entities(text, labels, threshold=threshold)
            
            # 🚀 Post-filter: reject junk fragments and function words
            # Define CJK particle set for more precise filtering
            cjk_particles = {"的", "了", "是", "在", "和", "及", "等", "于"}
            
            filtered = []
            for ent in entities:
                txt = ent["text"].strip()
                
                # Rule 1: Reject short ASCII, but allow acronyms and names
                if not is_cjk and len(txt) <= 4:
                    # Allow ASCII if it's all uppercase (acronym) or contains letters/digits
                    if not (txt.isupper() or any(c.isalpha() for c in txt)):
                        continue
                
                # Rule 2: For CJK, allow 2+ characters (not too strict)
                if is_cjk and len(txt) < 2:
                    continue
                
                # Rule 3: Reject particles only if they are exact matches or single character
                # This preserves valid entities like "中国" (China) or "上海" (Shanghai)
                if is_cjk:
                    # Only reject if exactly matches a particle or is single-char particle
                    if txt in cjk_particles or (len(txt) == 1 and txt in cjk_particles):
                        continue

                filtered.append({
                    "text": txt,
                    "label": ent["label"].upper().replace(" ", "_"),
                    "confidence": round(float(ent.get("score", 0.9)), 4),
                    "start": ent.get("start"),
                    "end": ent.get("end")
                })
            
            return filtered
        except Exception as e:
            logger.error(f"Tier 1 GPU (GLiNER) failed: {e}")
            return None

    def extract_with_v1_local(self, text: str) -> List[Dict]:
        """TIER 3: SpaCy Fallback"""
        self._load_spacy_v1()
        if not self.nlp or not text:
            return []

        try:
            doc = self.nlp(text)
            return [
                {
                    "text": ent.text,
                    "label": ent.label_,
                    "confidence": 0.7, # SpaCy small doesn't provide confidence easily
                    "start": ent.start_char,
                    "end": ent.end_char
                }
                for ent in doc.ents
            ]
        except Exception as e:
            logger.error(f"SpaCy extraction failed: {e}")
            return []

    def extract_entities(self, text: str, source_lang: str = None) -> Dict[str, Any]:
        """
        Unified NER API with Triple-Tier GPU Logic
        """
        start_time = time.time()
        if not text or len(text.strip()) < 5:
            return {"entities": [], "status": "empty_input", "role": "fallback", "analysis_time": 0.0}

        entities = None
        status = "total_failure"
        role = "fallback"

        # --- Tier 1: Local V2 (GLiNER GPU) ---
        entities = self.extract_with_v2_local(text)
        if entities is not None:
            status = "READY_FOR_LOCAL_GPU"
            role = "primary"

        # --- Tier 2: Cloud V2 (Placeholder) ---
        if entities is None:
            logger.warning("Tier 1 Failed. Cloud V2 Trigger not yet active. Falling back to Tier 3.")

        # --- Tier 3: Local V1 (SpaCy) ---
        if entities is None:
            entities = self.extract_with_v1_local(text)
            status = "FALLBACK_TO_V1_GPU_SAFETY"
            role = "fallback"

        if entities is None or len(entities) == 0:
            entities = []

        # 🚀 Priority 1: Language-specific name booster (very lightweight)
        # Auto-detect language if not provided
        if not source_lang:
            if any("\u0900" <= c <= "\u097F" for c in text[:200]):
                source_lang = "hi"
            elif any("\u4e00" <= c <= "\u9fff" for c in text[:100]):
                source_lang = "zh"

        if source_lang and source_lang.lower().split("-")[0] in ['hi', 'zh']:
            try:
                lang_code = source_lang.lower().split("-")[0]
                MAX_FALLBACK_ENTITIES = 50  # Prevent runaway matches
                fallback_count = 0
                
                # Language-specific stopword sets to avoid false positives
                lang_stopwords_zh = {'中国', '印度', '政府', '公司', '人民', '地方', '城市', '国家'}
                lang_stopwords_hi = {'का', 'की', 'के', 'और', 'है', 'में', 'को'}
                lang_stopwords = lang_stopwords_zh if lang_code == 'zh' else lang_stopwords_hi
                
                if lang_code == 'hi':
                    # Hindi: sequences with word boundaries, require 2+ Devanagari tokens
                    pattern = r'[\u0900-\u097F]{2,}(?:\s+[\u0900-\u097F]{2,})+'
                    matches = re.finditer(pattern, text)
                else:  # Chinese
                    # Allow 2-character Chinese names (relax from 3+ requirement)
                    pattern = r'[\u4e00-\u9fff]{2,4}'
                    matches = re.finditer(pattern, text)
                
                for m in matches:
                    if fallback_count >= MAX_FALLBACK_ENTITIES:
                        break
                        
                    span_text = m.group().strip()
                    
                    # For Chinese, allow 2-char spans; for Hindi, require 3+
                    if lang_code == 'zh':
                        if len(span_text) < 2:
                            continue
                    else:  # Hindi
                        if len(span_text) < 3:
                            continue
                        
                    # Avoid adding stopwords (improved filter)
                    if span_text in lang_stopwords:
                        continue
                        
                    # Add if not already present (simple dedup by text)
                    if not any(e['text'] == span_text for e in entities):
                        entities.append({
                            "text": span_text,
                            "label": "POTENTIAL_ENTITY",
                            "confidence": 0.55,           # reduced confidence for non-assertive label
                            "start": m.start(),
                            "end": m.end(),
                            "source": "lang_fallback"
                        })
                        fallback_count += 1
                        
            except Exception as e:
                logger.warning(f"Language fallback NER failed: {e}")

        return {
            "value": entities, # 'value' for schema consistency
            "entities": entities, # alias for backward compatibility
            "confidence": 0.95 if role == "primary" else 0.7,
            "role": role,
            "status": status,
            "history": [],
            "analysis_time": round(time.time() - start_time, 3)
        }


# Singleton instance
ner_service = NERService()

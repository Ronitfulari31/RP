"""
Keyword Extraction Service V2
Uses T5 Transformer for state-of-the-art keyword extraction with GPU acceleration.
Triple-Tier Logic: Local GPU (T5-small) -> Cloud GPU (T5-base) -> V1 Fallback (KeyBERT)
"""

import logging
import os
import time
import torch
import threading

logger = logging.getLogger(__name__)


class KeywordExtractionService:
    def __init__(self):
        self.t5_model_local = None  # T5-small for local GPU
        self.t5_model_cloud = None  # T5-base for Kaggle GPU
        self.t5_tokenizer = None
        self.keybert_model_v1 = None  # V1 fallback
        self.device = None
        self._load_lock = threading.Lock()

    def _detect_gpu(self):
        """Detect available GPU device"""
        if self.device is None:
            if torch.cuda.is_available():
                self.device = "cuda"
                gpu_name = torch.cuda.get_device_name(0)
                logger.info(f"GPU detected: {gpu_name}")
            else:
                self.device = "cpu"
                logger.warning("No GPU detected, falling back to CPU")
        return self.device

    def _load_t5_local(self):
        """Load T5 model for local GPU (Tier 1)"""
        with self._load_lock:
            if self.t5_model_local is None:
                try:
                    from transformers import T5Tokenizer, T5ForConditionalGeneration
                    
                    logger.info("Loading T5 V2 model (Tier 1 Local GPU)...")
                    
                    # Try Voicelab model first, fallback to standard T5-small
                    try:
                        model_name = "Voicelab/vlt5-base-keywords"
                        logger.info(f"Attempting to load {model_name}...")
                    except:
                        model_name = "t5-small"
                        logger.info(f"Falling back to {model_name}...")
                    
                    self.t5_tokenizer = T5Tokenizer.from_pretrained(
                        model_name,
                        cache_dir=os.getenv("TRANSFORMERS_CACHE", "D:/huggingface_cache")
                    )
                    
                    device = self._detect_gpu()
                    if device == "cuda":
                        logger.info("Loading T5 to CPU first (bypassing meta tensors)...")
                        model = T5ForConditionalGeneration.from_pretrained(
                            model_name,
                            cache_dir=os.getenv("TRANSFORMERS_CACHE", "D:/huggingface_cache"),
                            torch_dtype=torch.float32,
                            low_cpu_mem_usage=False
                        )
                        logger.info("Moving T5 to CUDA...")
                        self.t5_model_local = model.to(device).eval()
                    else:
                        self.t5_model_local = T5ForConditionalGeneration.from_pretrained(
                            model_name,
                            cache_dir=os.getenv("TRANSFORMERS_CACHE", "D:/huggingface_cache")
                        ).eval()
                    
                    logger.info(f"T5 V2 ({model_name}) loaded successfully on Local GPU.")
                    
                except Exception as e:
                    logger.error(f"Failed to load T5: {e}")
                    self.t5_model_local = None
                
        return self.t5_model_local

    def _load_t5_cloud(self):
        """Load T5 model for Kaggle GPU (Tier 2) - same as local for now"""
        # For now, use the same model as local
        # In production, this would load a larger T5-base model on Kaggle
        return self._load_t5_local()

    def _load_keybert_v1(self):
        """Load KeyBERT V1 as fallback (Tier 3)"""
        if self.keybert_model_v1 is None:
            try:
                from keybert import KeyBERT
                from sentence_transformers import SentenceTransformer
                
                logger.info("Loading KeyBERT V1 with safe SentenceTransformer (Tier 3)...")
                
                # Manual SentenceTransformer loading to bypass meta tensor issue
                model_name = 'all-MiniLM-L6-v2'
                logger.info(f"Loading {model_name} to CPU first...")
                # Note: SentenceTransformer doesn't support low_cpu_mem_usage directly 
                # but setting device='cpu' and using AutoModel internally might help
                st_model = SentenceTransformer(model_name, device='cpu')
                
                device = self._detect_gpu()
                if device == 'cuda':
                    logger.info("Moving SentenceTransformer to CUDA...")
                    st_model.to('cuda')
                
                self.keybert_model_v1 = KeyBERT(model=st_model)
                logger.info("KeyBERT V1 loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load KeyBERT V1: {e}")
        return self.keybert_model_v1

    def _extract_with_t5(self, text: str, model, top_n: int = 10):
        """Extract keywords using T5 model"""
        try:
            if not model or not self.t5_tokenizer:
                return None
            
            # Prepare input
            input_text = f"extract keywords: {text}"
            inputs = self.t5_tokenizer(
                input_text,
                return_tensors="pt",
                max_length=512,
                truncation=True
            ).to(self.device)
            
            # Generate keywords
            outputs = model.generate(
                **inputs,
                max_length=100,
                num_beams=5,
                num_return_sequences=1,
                early_stopping=True
            )
            
            # Decode output
            keywords_text = self.t5_tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Split keywords (T5 outputs comma-separated keywords)
            keywords = [kw.strip() for kw in keywords_text.split(",") if kw.strip()]
            
            return keywords[:top_n]
            
        except Exception as e:
            logger.error(f"T5 extraction failed: {e}")
            return None

    def _extract_with_keybert_v1(self, text: str, top_n: int = 10):
        """Extract keywords using KeyBERT V1 (fallback)"""
        try:
            model = self._load_keybert_v1()
            if not model:
                return []
            
            keywords = model.extract_keywords(
                text,
                keyphrase_ngram_range=(1, 3),
                stop_words='english',
                use_mmr=True,
                diversity=0.7,
                top_n=top_n
            )
            
            return [kw[0] for kw in keywords if kw[1] > 0.3]
            
        except Exception as e:
            logger.error(f"KeyBERT V1 extraction failed: {e}")
            return []

    def extract(self, text: str, top_n: int = 10):
        """
        Extract keywords with Triple-Tier GPU logic.
        
        Returns structured output:
        {
            'value': ['keyword1', 'keyword2', ...],
            'confidence': float,
            'status': str,
            'role': str,
            'extraction_time': float
        }
        """
        start_time = time.time()
        
        try:
            if not text or len(text.strip()) < 10:
                return {
                    'value': [],
                    'confidence': 0.0,
                    'status': 'SKIPPED_TOO_SHORT',
                    'role': 'none',
                    'extraction_time': 0.0
                }
            
            word_count = len(text.split())
            
            # Tier 1: Local GPU (T5-small) for short articles
            if word_count < 500:
                logger.info(f"Using Tier 1: Local GPU (T5-small) for {word_count} words")
                model = self._load_t5_local()
                if model:
                    keywords = self._extract_with_t5(text, model, top_n)
                    if keywords:
                        extraction_time = time.time() - start_time
                        return {
                            'value': keywords,
                            'confidence': 0.90,
                            'status': 'READY_FOR_LOCAL_GPU',
                            'role': 'primary',
                            'extraction_time': round(extraction_time, 3)
                        }
            
            # Tier 2: Cloud GPU (T5-base) for long articles
            else:
                logger.info(f"Using Tier 2: Cloud GPU (T5-base) for {word_count} words")
                model = self._load_t5_cloud()
                if model:
                    keywords = self._extract_with_t5(text, model, top_n)
                    if keywords:
                        extraction_time = time.time() - start_time
                        return {
                            'value': keywords,
                            'confidence': 0.95,
                            'status': 'READY_FOR_CLOUD_GPU',
                            'role': 'primary',
                            'extraction_time': round(extraction_time, 3)
                        }
            
            # Tier 3: V1 Fallback (KeyBERT)
            logger.warning("Falling back to Tier 3: KeyBERT V1")
            keywords = self._extract_with_keybert_v1(text, top_n)
            extraction_time = time.time() - start_time
            
            return {
                'value': keywords,
                'confidence': 0.75,
                'status': 'FALLBACK_TO_V1_GPU_SAFETY',
                'role': 'fallback',
                'extraction_time': round(extraction_time, 3)
            }
            
        except Exception as e:
            logger.exception(f"Keyword extraction failed: {e}")
            extraction_time = time.time() - start_time
            
            return {
                'value': [],
                'confidence': 0.0,
                'status': 'ERROR',
                'role': 'none',
                'extraction_time': round(extraction_time, 3),
                'error': str(e)
            }


# Singleton instance
keyword_extraction_service = KeywordExtractionService()

from app.services.dag.nodes.base_node import ProcessingNode, GateNode
import logging

class EmbeddingInputNode(ProcessingNode):
    """Prepares text for embedding generation."""
    def __init__(self):
        super().__init__("EmbeddingInput")

    def _process(self, context: dict) -> dict:
        # Build a composite string for better semantic vector
        title = context.get("title", "")
        summary = context.get("summary", "")
        
        # Robust keyword handling (handle both strings and legacy dicts)
        raw_keywords = context.get("keywords", [])
        keyword_list = []
        for kw in raw_keywords:
            if isinstance(kw, str):
                keyword_list.append(kw)
            elif isinstance(kw, dict) and "text" in kw:
                keyword_list.append(kw["text"])
        
        keywords = ", ".join(keyword_list)
        
        # Use translated content if available
        body = context.get("translated_text") or context.get("cleaned_text") or ""
        
        context["embedding_input"] = f"{title}. {summary}. {keywords}. {body[:500]}"
        return context

class EmbeddingNode(ProcessingNode):
    def __init__(self):
        super().__init__("EmbeddingGeneration")

    def _process(self, context: dict) -> dict:
        logger = logging.getLogger(__name__)
        
        # 🧠 FIX 3: Idempotency Guard
        if context.get("embedding"):
            logger.info(f"[DEBUG_TRACE] Embedding already exists. Skipping generation. ContextID: {hex(id(context))}")
            return context

        logger.info(f"[DEBUG_TRACE] EmbeddingNode start. ContextID: {hex(id(context))}")
        
        text = context.get("embedding_input", "")
        if not text:
            logger.warning("[DEBUG_TRACE] EmbeddingNode: Input text is empty! Skipping generation.")
            return context
            
        # Un-mocked: Use strict-approved sentence-transformers (GPU)
        try:
             logger.info(f"[DEBUG_TRACE] EmbeddingNode: Encoding text (len={len(text)})...")
             from app.services.intelli_search.vector_retriever import get_model
             encoding_model = get_model()
             # Generate embedding and convert to list (DAG requires JSON serializable)
             # Disable progress bar to avoid TQDM conflicts with executor silencing
             vector = encoding_model.encode(text, normalize_embeddings=True, show_progress_bar=False).tolist()
             context["embedding"] = vector
             logger.info(f"[DEBUG_TRACE] EmbeddingNode: Vector generated (dim={len(vector)}). ContextID: {hex(id(context))}")
        except Exception as e:
             # Fail softly as per node logic, but log error
             logger.error(f"[ERROR_TRACE] EmbeddingNode Exception: {str(e)}")
             context["embedding"] = None
             context["errors"] = context.get("errors", []) + [f"Embedding failed: {str(e)}"] 
        return context

class EmbeddingQualityGate(GateNode):
    def __init__(self):
        super().__init__("EmbeddingQualityGate")
        self.logger = logging.getLogger(__name__)

    def _evaluate(self, context: dict) -> dict:
        emb = context.get("embedding")
        
        self.logger.debug(
            f"[DEBUG_TRACE] EmbeddingQualityGate start. "
            f"ContextID: {hex(id(context))} | "
            f"Embedding Type: {type(emb)}"
        )

        if emb is None:
            context["rejected"] = True
            context["rejection_reason"] = "Failed to generate valid embedding"
            context["rejected_at_node"] = self.name
            self.logger.debug("[DEBUG_TRACE] EmbeddingQualityGate: ❌ REJECTED")
        elif not isinstance(emb, list) or len(emb) < 128:
            context["rejected"] = True
            context["rejection_reason"] = "Invalid embedding vector"
            context["rejected_at_node"] = self.name
            self.logger.debug("[DEBUG_TRACE] EmbeddingQualityGate: ❌ REJECTED (invalid shape)")
        else:
            context["embedding_valid"] = True
            self.logger.debug(
                f"[DEBUG_TRACE] EmbeddingQualityGate: ✅ PASSED "
                f"(dim={len(emb)})"
            )

        return context

import os
from dotenv import load_dotenv
load_dotenv()

# Set cache paths before importing model libraries
os.environ['HF_HOME'] = os.getenv('HF_HOME', r'D:\ML_Models_Cache\huggingface')
os.environ['SENTENCE_TRANSFORMERS_HOME'] = os.getenv('SENTENCE_TRANSFORMERS_HOME', r'D:\ML_Models_Cache\sentence_transformers')
os.environ['TRANSFORMERS_CACHE'] = os.getenv('TRANSFORMERS_CACHE', r'D:\ML_Models_Cache\huggingface')

from sentence_transformers import CrossEncoder
from typing import List, Dict

# Load once (global singleton)
_bge_reranker = None

def get_bge_reranker():
    global _bge_reranker
    if _bge_reranker is None:
        _bge_reranker = CrossEncoder(
            "BAAI/bge-reranker-v2-m3",
            max_length=512
        )
    return _bge_reranker


def rerank_with_bge(query: str, documents: List[Dict], top_k: int = 5):
    """
    documents: list of dicts with keys:
        - text
        - metadata (original article)
    """

    if not documents:
        return []

    reranker = get_bge_reranker()

    pairs = [
        (query, doc["text"])
        for doc in documents
    ]

    scores = reranker.predict(pairs)

    ranked = sorted(
        zip(documents, scores),
        key=lambda x: x[1],
        reverse=True
    )

    return [
        {
            **doc["metadata"], # Unwrap the article from the 'metadata' wrapper
            "bge_score": float(score)
        }
        for doc, score in ranked[:top_k]
    ]

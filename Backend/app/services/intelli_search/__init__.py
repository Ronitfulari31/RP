"""
IntelliNews Search Service
High-accuracy intelligent search using Ollama LLM and semantic ranking.
"""

from .ollama_client import get_ollama_llm
from .query_processor import process_query
from .retriever import retrieve_candidates
from .reranker import rerank

__all__ = ["get_ollama_llm", "process_query", "retrieve_candidates", "rerank"]

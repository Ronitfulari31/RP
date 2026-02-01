from langchain_ollama import ChatOllama
import os

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

def get_ollama_llm(temperature: float = 0.2):
    """
    Returns a configured Ollama LLM instance.
    Used for query understanding, expansion, and reranking.
    """
    return ChatOllama(
        base_url=OLLAMA_BASE_URL,
        model=OLLAMA_MODEL,
        temperature=temperature,
    )

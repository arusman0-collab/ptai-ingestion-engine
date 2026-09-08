"""Embedding backend interface and Ollama implementation."""
from __future__ import annotations
from typing import Protocol
import httpx

DOCUMENT_PREFIX = "search_document: "
QUERY_PREFIX = "search_query: "

class EmbeddingService(Protocol):
    model: str
    dimensions: int
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, query: str) -> list[float]: ...

class OllamaEmbeddingService:
    def __init__(self, url: str, model: str, dimensions: int):
        self.url, self.model, self.dimensions = url.rstrip("/"), model, dimensions
    def _embed(self, inputs: list[str]) -> list[list[float]]:
        response = httpx.post(f"{self.url}/api/embed", json={"model": self.model, "input": inputs}, timeout=60)
        response.raise_for_status()
        values = response.json().get("embeddings")
        if not isinstance(values, list) or any(len(v) != self.dimensions for v in values):
            raise RuntimeError(f"Ollama embedding dimensions do not match configured {self.dimensions}")
        return values
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed([DOCUMENT_PREFIX + text for text in texts])
    def embed_query(self, query: str) -> list[float]:
        return self._embed([QUERY_PREFIX + query])[0]
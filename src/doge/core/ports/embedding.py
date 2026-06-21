"""Embedding provider and cache ports."""

from __future__ import annotations

from typing import Protocol


class IEmbeddingProvider(Protocol):
    """Convert text into deterministic vector representations."""

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        ...


class IEmbeddingCache(Protocol):
    """Cache embeddings by stable content hash."""

    def get(self, key: str) -> list[float] | None:
        ...

    def set(self, key: str, vector: list[float]) -> None:
        ...

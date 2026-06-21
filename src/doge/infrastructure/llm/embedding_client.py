"""Local deterministic embedding provider for offline RAG tests."""

from __future__ import annotations

import hashlib
import math
import re

from doge.core.ports.embedding import IEmbeddingProvider


class HashingEmbeddingProvider(IEmbeddingProvider):
    """Small hashing-vector provider with no network dependency."""

    def __init__(self, dimensions: int = 64) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be positive")
        self._dimensions = dimensions

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self._dimensions
        for token in _tokens(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self._dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


def _tokens(text: str) -> list[str]:
    return re.findall(r"[\w\u4e00-\u9fff]+", text.lower())

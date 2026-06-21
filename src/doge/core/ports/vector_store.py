"""Vector store port for local RAG retrieval."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class VectorRecord:
    record_id: str
    vector: list[float]
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VectorSearchResult:
    record: VectorRecord
    score: float


class IVectorStore(Protocol):
    def upsert(self, records: list[VectorRecord]) -> None:
        ...

    def search(
        self,
        vector: list[float],
        *,
        top_k: int = 5,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        ...

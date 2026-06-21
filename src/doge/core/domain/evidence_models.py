"""Domain models for evidence linked to document chunks."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from doge.core.domain.agent_models import utc_now
from doge.core.domain.chunk_models import DocumentChunk


@dataclass(frozen=True)
class EvidenceRecord:
    """A support snippet that ties a claim or answer back to a source chunk."""

    evidence_id: str
    document_id: str
    chunk_id: str
    page_id: str
    page_number: int
    support_snippet: str
    claim: str = ""
    run_id: str | None = None
    relevance_score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        *,
        chunk: DocumentChunk,
        support_snippet: str,
        claim: str = "",
        run_id: str | None = None,
        relevance_score: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "EvidenceRecord":
        evidence_id = _stable_evidence_id(
            run_id or "",
            chunk.document_id,
            chunk.chunk_id,
            claim,
            support_snippet,
        )
        return cls(
            evidence_id=evidence_id,
            run_id=run_id,
            document_id=chunk.document_id,
            page_id=chunk.page_id,
            chunk_id=chunk.chunk_id,
            page_number=chunk.page_number,
            claim=claim,
            support_snippet=support_snippet,
            relevance_score=relevance_score,
            metadata=metadata or {},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "run_id": self.run_id,
            "document_id": self.document_id,
            "page_id": self.page_id,
            "chunk_id": self.chunk_id,
            "page_number": self.page_number,
            "claim": self.claim,
            "support_snippet": self.support_snippet,
            "relevance_score": self.relevance_score,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "EvidenceRecord":
        metadata = data.get("metadata") or {}
        if isinstance(metadata, str):
            metadata = json.loads(metadata or "{}")
        return cls(
            evidence_id=data["evidence_id"],
            run_id=data.get("run_id"),
            document_id=data["document_id"],
            page_id=data["page_id"],
            chunk_id=data["chunk_id"],
            page_number=int(data["page_number"]),
            claim=data.get("claim") or "",
            support_snippet=data.get("support_snippet") or "",
            relevance_score=data.get("relevance_score"),
            metadata=metadata,
            created_at=data.get("created_at") or utc_now(),
        )


def _stable_evidence_id(*parts: str) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"evd-{digest}"

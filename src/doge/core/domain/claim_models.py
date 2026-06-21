"""Domain models for report claims and citations."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from doge.core.domain.agent_models import utc_now


@dataclass(frozen=True)
class ClaimRecord:
    """A material claim extracted from a generated research artifact."""

    claim_id: str
    report_id: str
    text: str
    status: str = "insufficient_evidence"
    evidence_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        *,
        report_id: str,
        text: str,
        status: str = "insufficient_evidence",
        evidence_count: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> "ClaimRecord":
        return cls(
            claim_id=_stable_id("clm", report_id, text),
            report_id=report_id,
            text=text,
            status=status,
            evidence_count=evidence_count,
            metadata=metadata or {},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "report_id": self.report_id,
            "text": self.text,
            "status": self.status,
            "evidence_count": self.evidence_count,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "ClaimRecord":
        metadata = data.get("metadata") or {}
        if isinstance(metadata, str):
            metadata = json.loads(metadata or "{}")
        return cls(
            claim_id=data["claim_id"],
            report_id=data["report_id"],
            text=data["text"],
            status=data.get("status") or "insufficient_evidence",
            evidence_count=int(data.get("evidence_count") or 0),
            metadata=metadata,
            created_at=data.get("created_at") or utc_now(),
        )


@dataclass(frozen=True)
class CitationRecord:
    """A citation from a report claim to a source chunk/page."""

    citation_id: str
    claim_id: str
    report_id: str
    source: str
    snippet: str
    document_id: str | None = None
    page_number: int | None = None
    chunk_id: str | None = None
    evidence_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        *,
        claim_id: str,
        report_id: str,
        source: str,
        snippet: str,
        document_id: str | None = None,
        page_number: int | None = None,
        chunk_id: str | None = None,
        evidence_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "CitationRecord":
        return cls(
            citation_id=_stable_id("cit", report_id, claim_id, source, snippet),
            claim_id=claim_id,
            report_id=report_id,
            source=source,
            snippet=snippet,
            document_id=document_id,
            page_number=page_number,
            chunk_id=chunk_id,
            evidence_id=evidence_id,
            metadata=metadata or {},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "citation_id": self.citation_id,
            "claim_id": self.claim_id,
            "report_id": self.report_id,
            "source": self.source,
            "snippet": self.snippet,
            "document_id": self.document_id,
            "page_number": self.page_number,
            "chunk_id": self.chunk_id,
            "evidence_id": self.evidence_id,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "CitationRecord":
        metadata = data.get("metadata") or {}
        if isinstance(metadata, str):
            metadata = json.loads(metadata or "{}")
        page_number = data.get("page_number")
        return cls(
            citation_id=data["citation_id"],
            claim_id=data["claim_id"],
            report_id=data["report_id"],
            source=data.get("source") or "",
            snippet=data.get("snippet") or "",
            document_id=data.get("document_id"),
            page_number=int(page_number) if page_number is not None else None,
            chunk_id=data.get("chunk_id"),
            evidence_id=data.get("evidence_id"),
            metadata=metadata,
            created_at=data.get("created_at") or utc_now(),
        )


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"

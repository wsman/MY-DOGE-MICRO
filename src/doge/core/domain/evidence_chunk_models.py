"""Domain models for evidence chunks linked to tool results and runs."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from doge.core.domain.agent_models import utc_now


@dataclass(frozen=True)
class EvidenceChunk:
    """A chunk of evidence extracted from a tool result, tied to a specific run.

    Attributes:
        evidence_id: Stable identifier for this evidence chunk.
        document_id: Identifier of the source document (if from a document).
        page_number: Page number within the source document (1-based).
        chunk_id: Identifier of the parent chunk (if from a document chunk).
        text: The textual content of this evidence snippet.
        source_tool: Name of the tool that produced this evidence.
        run_id: Identifier of the agent run that produced this evidence.
        created_at: ISO-8601 timestamp of creation.
    """

    evidence_id: str
    document_id: str
    page_number: int
    chunk_id: str
    text: str
    source_tool: str
    run_id: str | None = None
    created_at: str = field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        *,
        document_id: str,
        page_number: int,
        chunk_id: str,
        text: str,
        source_tool: str,
        run_id: str | None = None,
    ) -> "EvidenceChunk":
        """Create an EvidenceChunk with a stable evidence_id."""
        evidence_id = _stable_evidence_id(
            run_id or "",
            document_id,
            chunk_id,
            source_tool,
            text,
        )
        return cls(
            evidence_id=evidence_id,
            document_id=document_id,
            page_number=page_number,
            chunk_id=chunk_id,
            text=text,
            source_tool=source_tool,
            run_id=run_id,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "document_id": self.document_id,
            "page_number": self.page_number,
            "chunk_id": self.chunk_id,
            "text": self.text,
            "source_tool": self.source_tool,
            "run_id": self.run_id,
            "created_at": self.created_at,
        }

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "EvidenceChunk":
        return cls(
            evidence_id=data["evidence_id"],
            document_id=data["document_id"],
            page_number=int(data["page_number"]),
            chunk_id=data["chunk_id"],
            text=data.get("text") or "",
            source_tool=data.get("source_tool") or "",
            run_id=data.get("run_id"),
            created_at=data.get("created_at") or utc_now(),
        )


def _stable_evidence_id(*parts: str) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"evd-{digest}"


__all__ = ["EvidenceChunk", "_stable_evidence_id"]

"""Domain models for deterministic document chunks."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from doge.core.domain.agent_models import utc_now
from doge.core.domain.page_models import DocumentPage


@dataclass(frozen=True)
class DocumentChunk:
    """A citeable span of text within a document page."""

    chunk_id: str
    document_id: str
    page_id: str
    page_number: int
    text: str
    start_char: int
    end_char: int
    source_hash: str | None = None
    created_at: str = field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        *,
        page: DocumentPage,
        text: str,
        start_char: int,
        end_char: int,
    ) -> "DocumentChunk":
        chunk_id = _stable_chunk_id(
            page.document_id,
            page.page_id,
            str(page.page_number),
            str(start_char),
            str(end_char),
            text,
        )
        return cls(
            chunk_id=chunk_id,
            document_id=page.document_id,
            page_id=page.page_id,
            page_number=page.page_number,
            text=text,
            start_char=start_char,
            end_char=end_char,
            source_hash=page.source_hash,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "page_id": self.page_id,
            "page_number": self.page_number,
            "text": self.text,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "source_hash": self.source_hash,
            "created_at": self.created_at,
        }

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "DocumentChunk":
        return cls(
            chunk_id=data["chunk_id"],
            document_id=data["document_id"],
            page_id=data["page_id"],
            page_number=int(data["page_number"]),
            text=data.get("text") or "",
            start_char=int(data.get("start_char") or 0),
            end_char=int(data.get("end_char") or 0),
            source_hash=data.get("source_hash"),
            created_at=data.get("created_at") or utc_now(),
        )


def _stable_chunk_id(*parts: str) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"chk-{digest}"

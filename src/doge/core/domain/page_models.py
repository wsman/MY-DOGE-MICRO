"""Domain models for extracted document pages."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from doge.core.domain.agent_models import utc_now


@dataclass(frozen=True)
class DocumentPage:
    """A page-like unit extracted from a registered document."""

    page_id: str
    document_id: str
    page_number: int
    text: str = ""
    source_hash: str | None = None
    image_metadata: dict[str, Any] = field(default_factory=dict)
    parser_error: str | None = None
    created_at: str = field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        *,
        document_id: str,
        page_number: int,
        text: str = "",
        source_hash: str | None = None,
        image_metadata: dict[str, Any] | None = None,
        parser_error: str | None = None,
    ) -> "DocumentPage":
        page_id = _stable_id("page", document_id, str(page_number), source_hash or "", text[:200])
        return cls(
            page_id=page_id,
            document_id=document_id,
            page_number=page_number,
            text=text,
            source_hash=source_hash,
            image_metadata=image_metadata or {},
            parser_error=parser_error,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_id": self.page_id,
            "document_id": self.document_id,
            "page_number": self.page_number,
            "text": self.text,
            "source_hash": self.source_hash,
            "image_metadata": self.image_metadata,
            "parser_error": self.parser_error,
            "created_at": self.created_at,
        }

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "DocumentPage":
        metadata = data.get("image_metadata") or {}
        if isinstance(metadata, str):
            metadata = json.loads(metadata or "{}")
        return cls(
            page_id=data["page_id"],
            document_id=data["document_id"],
            page_number=int(data["page_number"]),
            text=data.get("text") or "",
            source_hash=data.get("source_hash"),
            image_metadata=metadata,
            parser_error=data.get("parser_error"),
            created_at=data.get("created_at") or utc_now(),
        )


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"

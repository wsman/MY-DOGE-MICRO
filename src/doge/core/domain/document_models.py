"""Domain model for uploaded research documents."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from doge.core.domain.agent_models import utc_now


class DocumentStatus(str, Enum):
    """Lifecycle states for a registered or uploaded document."""

    REGISTERED = "registered"
    UPLOADED = "uploaded"
    PARSING = "parsing"
    PARSED = "parsed"
    FAILED = "failed"


@dataclass(frozen=True)
class Document:
    """Persisted metadata for a real research document."""

    document_id: str
    original_filename: str
    file_hash: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    storage_path: Optional[str] = None
    kimi_file_id: Optional[str] = None
    parsing_status: DocumentStatus = DocumentStatus.REGISTERED
    parser_error: Optional[str] = None
    content: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def create(
        cls,
        *,
        original_filename: str,
        file_hash: str | None = None,
        mime_type: str | None = None,
        size_bytes: int | None = None,
        storage_path: str | None = None,
        kimi_file_id: str | None = None,
        parsing_status: DocumentStatus = DocumentStatus.REGISTERED,
        parser_error: str | None = None,
        content: str | None = None,
        document_id: str | None = None,
    ) -> "Document":
        now = utc_now()
        return cls(
            document_id=document_id or f"doc-{uuid4().hex[:12]}",
            original_filename=original_filename,
            file_hash=file_hash,
            mime_type=mime_type,
            size_bytes=size_bytes,
            storage_path=storage_path,
            kimi_file_id=kimi_file_id,
            parsing_status=parsing_status,
            parser_error=parser_error,
            content=content,
            created_at=now,
            updated_at=now,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "document_id": self.document_id,
            "filename": self.original_filename,
            "original_filename": self.original_filename,
            "file_hash": self.file_hash,
            "mime_type": self.mime_type,
            "size_bytes": self.size_bytes,
            "storage_path": self.storage_path,
            "kimi_file_id": self.kimi_file_id,
            "parsing_status": self.parsing_status.value,
            "parser_error": self.parser_error,
            "content": self.content,
            "status": self.parsing_status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "Document":
        status = data.get("parsing_status") or data.get("status") or DocumentStatus.REGISTERED.value
        if status == "ready":
            status = DocumentStatus.PARSED.value
        return cls(
            document_id=data["document_id"],
            original_filename=data.get("original_filename") or data.get("filename") or data["document_id"],
            file_hash=data.get("file_hash"),
            mime_type=data.get("mime_type"),
            size_bytes=data.get("size_bytes"),
            storage_path=data.get("storage_path"),
            kimi_file_id=data.get("kimi_file_id"),
            parsing_status=DocumentStatus(status),
            parser_error=data.get("parser_error") or data.get("error_message"),
            content=data.get("content") or data.get("parsed_content"),
            created_at=data.get("created_at") or utc_now(),
            updated_at=data.get("updated_at") or data.get("created_at") or utc_now(),
        )

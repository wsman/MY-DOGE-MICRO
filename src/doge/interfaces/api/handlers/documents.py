"""Document API handlers without FastAPI dependencies."""

from __future__ import annotations

from dataclasses import dataclass

from doge.shared.scope import TenantScope


@dataclass(frozen=True)
class UploadDocumentCommand:
    filename: str
    content: str = ""
    document_id: str | None = None
    payload: bytes | None = None


class UploadDocumentHandler:
    def __init__(self, *, upload_service) -> None:
        self._upload_service = upload_service

    def handle(self, command: UploadDocumentCommand, *, scope: TenantScope):
        if command.payload is not None:
            return self._upload_service.register_bytes(
                filename=command.filename,
                payload=command.payload,
                scope=scope,
            )
        return self._upload_service.register_text(
            filename=command.filename,
            content=command.content,
            document_id=command.document_id,
            scope=scope,
        )

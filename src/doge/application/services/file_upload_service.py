"""Application service for registering real research files."""

from __future__ import annotations

import hashlib
import mimetypes
import shutil
from pathlib import Path
from typing import Protocol

from doge.application.services.file_purpose_router import route_kimi_file_purpose
from doge.core.domain.document_models import Document, DocumentStatus
from doge.core.ports.document_repository import IDocumentRepository


class FileUploadError(ValueError):
    """Safe, user-facing upload validation error."""


class KimiFilesPort(Protocol):
    def upload_file(self, path: Path, *, purpose: str = "file-extract") -> str:
        ...

    def get_file_content(self, file_id: str) -> str:
        ...


class DocumentParserPort(Protocol):
    def parse(self, path: str | Path, *, max_chars: int = 12000) -> str:
        ...


class DocumentExtractionPort(Protocol):
    def extract(self, document: Document | dict) -> object:
        ...


class FileUploadService:
    """Register local/API-uploaded files with hash, MIME, size and status."""

    DEFAULT_ALLOWED_SUFFIXES = {
        ".pdf", ".txt", ".csv", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".md", ".jpeg", ".jpg", ".png", ".bmp", ".gif", ".svg", ".webp", ".tif",
        ".tiff", ".html", ".json", ".jsonl", ".log", ".mp4", ".mov", ".avi", ".mkv", ".webm",
    }

    def __init__(
        self,
        repository: IDocumentRepository,
        *,
        storage_dir: Path,
        max_file_bytes: int = 100 * 1024 * 1024,
        allowed_suffixes: set[str] | None = None,
        parser: DocumentParserPort | None = None,
        kimi_files_client: KimiFilesPort | None = None,
        extraction_service: DocumentExtractionPort | None = None,
    ) -> None:
        self._repository = repository
        self._storage_dir = storage_dir
        self._max_file_bytes = max_file_bytes
        self._allowed_suffixes = {item.lower() for item in (allowed_suffixes or self.DEFAULT_ALLOWED_SUFFIXES)}
        self._parser = parser
        self._kimi_files_client = kimi_files_client
        self._extraction_service = extraction_service

    def register_path(self, path: str | Path) -> dict:
        source = Path(path).expanduser().resolve()
        if not source.exists() or not source.is_file():
            raise FileUploadError(f"file not found: {source}")
        self._validate_file(source.name, source.stat().st_size)
        payload = source.read_bytes()
        return self.register_bytes(filename=source.name, payload=payload)

    def register_bytes(self, *, filename: str, payload: bytes) -> dict:
        self._validate_file(filename, len(payload))
        file_hash = hashlib.sha256(payload).hexdigest()
        existing = self._repository.get_by_hash(file_hash)
        if existing is not None:
            self._extract(existing)
            return existing

        storage_path = self._persist_payload(filename, file_hash, payload)
        mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        purpose = route_kimi_file_purpose(filename=filename, mime_type=mime_type)
        kimi_file_id: str | None = None
        content: str | None = None
        parser_error: str | None = None
        status = DocumentStatus.UPLOADED

        if self._kimi_files_client is not None:
            try:
                kimi_file_id = self._kimi_files_client.upload_file(storage_path, purpose=purpose)
                if purpose == "file-extract":
                    content = self._kimi_files_client.get_file_content(kimi_file_id)
                    status = DocumentStatus.PARSED
            except Exception as exc:  # noqa: BLE001 - provider errors become safe metadata
                parser_error = f"kimi files upload failed: {type(exc).__name__}"
                status = DocumentStatus.FAILED

        if content is None and purpose == "file-extract" and status is not DocumentStatus.FAILED and self._parser is not None:
            try:
                content = self._parser.parse(storage_path)
                status = DocumentStatus.PARSED
            except Exception as exc:  # noqa: BLE001 - local parser failure is captured in metadata
                parser_error = f"local parser failed: {type(exc).__name__}"
                status = DocumentStatus.FAILED

        document = Document.create(
            original_filename=filename,
            file_hash=file_hash,
            mime_type=mime_type,
            size_bytes=len(payload),
            storage_path=str(storage_path),
            kimi_file_id=kimi_file_id,
            kimi_file_purpose=purpose,
            parsing_status=status,
            parser_error=parser_error,
            content=content,
        )
        return self._save_and_extract(document)

    def register_text(self, *, filename: str, content: str, document_id: str | None = None) -> dict:
        payload = content.encode("utf-8")
        file_hash = hashlib.sha256(payload).hexdigest()
        mime_type = mimetypes.guess_type(filename)[0] or "text/plain"
        document = Document.create(
            document_id=document_id,
            original_filename=filename,
            file_hash=file_hash,
            mime_type=mime_type,
            size_bytes=len(payload),
            parsing_status=DocumentStatus.PARSED,
            kimi_file_purpose=route_kimi_file_purpose(filename=filename, mime_type=mime_type),
            content=content,
        )
        return self._save_and_extract(document)

    def _validate_file(self, filename: str, size_bytes: int) -> None:
        if not filename:
            raise FileUploadError("filename is required")
        suffix = Path(filename).suffix.lower()
        if suffix not in self._allowed_suffixes:
            raise FileUploadError(f"unsupported file type: {suffix or '<none>'}")
        if size_bytes <= 0:
            raise FileUploadError("file is empty")
        if size_bytes > self._max_file_bytes:
            raise FileUploadError(f"file exceeds max size: {self._max_file_bytes} bytes")

    def _persist_payload(self, filename: str, file_hash: str, payload: bytes) -> Path:
        suffix = Path(filename).suffix.lower()
        destination_dir = self._storage_dir / file_hash[:2]
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination = destination_dir / f"{file_hash}{suffix}"
        if not destination.exists():
            tmp = destination.with_suffix(destination.suffix + ".tmp")
            tmp.write_bytes(payload)
            shutil.move(str(tmp), str(destination))
        return destination

    def _save_and_extract(self, document: Document) -> dict:
        self._repository.save(document)
        saved = self._repository.get(document.document_id)
        result = saved if saved is not None else document.to_dict()
        self._extract(result)
        return result

    def _extract(self, document: Document | dict) -> None:
        if self._extraction_service is not None:
            self._extraction_service.extract(document)

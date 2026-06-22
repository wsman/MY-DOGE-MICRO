"""Application services for document page extraction and chunking."""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from doge.core.domain.chunk_models import DocumentChunk
from doge.core.domain.document_models import Document
from doge.core.domain.page_models import DocumentPage
from doge.core.ports.evidence_repository import IEvidenceRepository


class PageParserPort(Protocol):
    def parse(self, path: str | Path, *, max_chars: int = 12000) -> str:
        ...


@dataclass(frozen=True)
class ExtractionResult:
    """Result of local page/chunk extraction for one document."""

    document_id: str
    pages: list[DocumentPage]
    chunks: list[DocumentChunk]
    errors: list[str]


class ChunkingService:
    """Split page text into deterministic citeable chunks."""

    def __init__(self, *, chunk_size: int = 1200, overlap: int = 120) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if overlap < 0:
            raise ValueError("overlap must be non-negative")
        self._chunk_size = chunk_size
        self._overlap = min(overlap, max(0, chunk_size - 1))

    def chunk_pages(self, pages: list[DocumentPage]) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        for page in pages:
            chunks.extend(self.chunk_page(page))
        return chunks

    def chunk_page(self, page: DocumentPage) -> list[DocumentChunk]:
        text = page.text or ""
        if not text.strip():
            return []
        chunks: list[DocumentChunk] = []
        start = 0
        length = len(text)
        while start < length:
            end = min(length, start + self._chunk_size)
            if end < length:
                split_at = _last_break_before(text, start, end)
                if split_at > start:
                    end = split_at
            chunk_text = text[start:end].strip()
            if chunk_text:
                leading_trim = len(text[start:end]) - len(text[start:end].lstrip())
                trailing_trim = len(text[start:end].rstrip())
                chunks.append(
                    DocumentChunk.create(
                        page=page,
                        text=chunk_text,
                        start_char=start + leading_trim,
                        end_char=start + trailing_trim,
                    )
                )
            if end >= length:
                break
            start = max(start + 1, end - self._overlap)
        return chunks


class PageExtractionService:
    """Extract pages/chunks and optionally persist them into evidence storage."""

    IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}

    def __init__(
        self,
        *,
        evidence_repository: IEvidenceRepository | None = None,
        parser: PageParserPort | None = None,
        chunking_service: ChunkingService | None = None,
        parser_max_chars: int = 12000,
    ) -> None:
        self._evidence_repository = evidence_repository
        self._parser = parser
        self._chunking = chunking_service or ChunkingService()
        self._parser_max_chars = parser_max_chars

    def extract(self, document: Document | dict) -> ExtractionResult:
        tenant_id = document.get("tenant_id") if isinstance(document, dict) else None
        doc = document if isinstance(document, Document) else Document.from_mapping(document)
        pages, errors = self._extract_pages(doc)
        chunks = self._chunking.chunk_pages(pages)
        if self._evidence_repository is not None:
            for page in pages:
                self._evidence_repository.save_page(page, tenant_id=tenant_id)
            for chunk in chunks:
                self._evidence_repository.save_chunk(chunk, tenant_id=tenant_id)
        return ExtractionResult(
            document_id=doc.document_id,
            pages=pages,
            chunks=chunks,
            errors=errors,
        )

    def _extract_pages(self, document: Document) -> tuple[list[DocumentPage], list[str]]:
        errors: list[str] = []
        path = Path(document.storage_path) if document.storage_path else None
        suffix = path.suffix.lower() if path else Path(document.original_filename).suffix.lower()
        if suffix in self.IMAGE_SUFFIXES:
            page = self._image_page(document, path)
            return [page], errors

        text = document.content or ""
        if not text and path is not None and self._parser is not None:
            try:
                text = self._parser.parse(path, max_chars=self._parser_max_chars)
            except Exception as exc:  # noqa: BLE001 - parser failures must be visible and safe
                error = f"{type(exc).__name__}: {exc}"
                errors.append(error)
                return [
                    DocumentPage.create(
                        document_id=document.document_id,
                        page_number=1,
                        source_hash=document.file_hash,
                        parser_error=error,
                    )
                ], errors

        parts = _split_page_text(text)
        pages = [
            DocumentPage.create(
                document_id=document.document_id,
                page_number=index,
                text=part,
                source_hash=document.file_hash,
            )
            for index, part in enumerate(parts, start=1)
        ]
        return pages or [
            DocumentPage.create(
                document_id=document.document_id,
                page_number=1,
                source_hash=document.file_hash,
            )
        ], errors

    def _image_page(self, document: Document, path: Path | None) -> DocumentPage:
        metadata = {
            "filename": document.original_filename,
            "mime_type": document.mime_type,
            "size_bytes": document.size_bytes,
            "file_hash": document.file_hash,
        }
        if path is not None and path.exists():
            metadata.update(_read_image_dimensions(path))
        text = (
            f"[image document: {document.original_filename}; "
            f"mime={document.mime_type or 'unknown'}; "
            f"bytes={document.size_bytes or 'unknown'}]"
        )
        return DocumentPage.create(
            document_id=document.document_id,
            page_number=1,
            text=text,
            source_hash=document.file_hash,
            image_metadata={key: value for key, value in metadata.items() if value is not None},
        )


def _split_page_text(text: str) -> list[str]:
    if not text:
        return []
    parts = [part.strip() for part in text.split("\f")]
    return [part for part in parts if part]


def _last_break_before(text: str, start: int, end: int) -> int:
    window = text[start:end]
    candidates = [window.rfind("\n\n"), window.rfind("\n"), window.rfind(". "), window.rfind(" ")]
    best = max(candidates)
    if best <= 0 or end - (start + best + 1) > 240:
        return end
    return start + best + 1


def _read_image_dimensions(path: Path) -> dict[str, int]:
    data = path.read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        width, height = struct.unpack(">II", data[16:24])
        return {"width": int(width), "height": int(height)}
    if data.startswith(b"\xff\xd8"):
        size = _jpeg_dimensions(data)
        if size is not None:
            width, height = size
            return {"width": width, "height": height}
    return {}


def _jpeg_dimensions(data: bytes) -> tuple[int, int] | None:
    index = 2
    while index + 9 < len(data):
        if data[index] != 0xFF:
            index += 1
            continue
        marker = data[index + 1]
        index += 2
        if marker in {0xD8, 0xD9}:
            continue
        if index + 2 > len(data):
            return None
        segment_length = int.from_bytes(data[index:index + 2], "big")
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            if index + 7 <= len(data):
                height = int.from_bytes(data[index + 3:index + 5], "big")
                width = int.from_bytes(data[index + 5:index + 7], "big")
                return width, height
            return None
        index += segment_length
    return None

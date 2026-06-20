"""File extraction facade."""

from __future__ import annotations

from pathlib import Path

from doge.infrastructure.documents.local_parser import LocalDocumentParser


class FileExtractor:
    """Small facade that can later swap local parsing for Kimi Files API."""

    def __init__(self, parser: LocalDocumentParser | None = None) -> None:
        self._parser = parser or LocalDocumentParser()

    def extract(self, path: str | Path) -> dict:
        file_path = Path(path)
        return {
            "document_id": f"doc-{file_path.stem}",
            "filename": file_path.name,
            "content": self._parser.parse(file_path),
        }

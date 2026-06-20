"""Local document parser for deterministic demo materials."""

from __future__ import annotations

from pathlib import Path


class LocalDocumentParser:
    """Read local demo documents as text snippets.

    The interview demo keeps extraction deterministic. Binary office/image
    formats degrade to a metadata snippet unless a real extractor is introduced.
    """

    TEXT_SUFFIXES = {".txt", ".md", ".csv", ".json", ".log"}

    def parse(self, path: str | Path, *, max_chars: int = 12000) -> str:
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(str(file_path))
        if file_path.suffix.lower() in self.TEXT_SUFFIXES:
            return file_path.read_text(encoding="utf-8", errors="replace")[:max_chars]
        return (
            f"[binary document: {file_path.name}; suffix={file_path.suffix}; "
            f"bytes={file_path.stat().st_size}]"
        )

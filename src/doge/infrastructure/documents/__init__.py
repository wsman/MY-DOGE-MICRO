"""Document extraction helpers for the research copilot demo."""

from doge.infrastructure.documents.file_extractor import FileExtractor
from doge.infrastructure.documents.local_parser import LocalDocumentParser
from doge.infrastructure.documents.slot import LocalDocumentParserSlot

__all__ = ["FileExtractor", "LocalDocumentParser", "LocalDocumentParserSlot"]

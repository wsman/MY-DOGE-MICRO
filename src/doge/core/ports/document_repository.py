"""Repository port for uploaded research documents."""

from __future__ import annotations

from abc import ABC, abstractmethod

from doge.core.domain.document_models import Document


class IDocumentRepository(ABC):
    """Persistence boundary for document metadata and extracted content."""

    @abstractmethod
    def save(self, document: Document | dict) -> None:
        ...

    @abstractmethod
    def get(self, document_id: str, tenant_id: str | None = None) -> dict | None:
        ...

    @abstractmethod
    def get_by_hash(self, file_hash: str, tenant_id: str | None = None) -> dict | None:
        ...

    @abstractmethod
    def list_recent(self, limit: int = 100, tenant_id: str | None = None) -> list[dict]:
        ...

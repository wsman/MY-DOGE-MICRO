"""Repository port for uploaded research documents."""

from __future__ import annotations

from abc import ABC, abstractmethod

from doge.core.domain.document_models import Document
from doge.shared.scope import TenantScope


class IDocumentRepository(ABC):
    """Persistence boundary for document metadata and extracted content."""

    @abstractmethod
    def save(self, document: Document | dict, scope: TenantScope) -> None:
        ...

    @abstractmethod
    def get(self, document_id: str, scope: TenantScope) -> dict | None:
        ...

    @abstractmethod
    def get_by_hash(self, file_hash: str, scope: TenantScope) -> dict | None:
        ...

    @abstractmethod
    def list_recent(self, scope: TenantScope, limit: int = 100) -> list[dict]:
        ...

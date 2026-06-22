"""Repository port for extracted pages, chunks, and evidence records."""

from __future__ import annotations

from typing import Protocol

from doge.core.domain.chunk_models import DocumentChunk
from doge.core.domain.evidence_models import EvidenceRecord
from doge.core.domain.page_models import DocumentPage


class IEvidenceRepository(Protocol):
    """Persist and retrieve the document evidence chain."""

    def save_page(self, page: DocumentPage, tenant_id: str | None = None) -> None:
        ...

    def list_pages(self, document_id: str, tenant_id: str | None = None) -> list[DocumentPage]:
        ...

    def save_chunk(self, chunk: DocumentChunk, tenant_id: str | None = None) -> None:
        ...

    def list_chunks(
        self,
        document_ids: list[str] | None = None,
        limit: int = 20,
        tenant_id: str | None = None,
    ) -> list[DocumentChunk]:
        ...

    def save_evidence(self, evidence: EvidenceRecord, tenant_id: str | None = None) -> None:
        ...

    def get_evidence(self, evidence_id: str, tenant_id: str | None = None) -> EvidenceRecord | None:
        ...

    def list_evidence(
        self,
        *,
        run_id: str | None = None,
        document_id: str | None = None,
        limit: int = 20,
        tenant_id: str | None = None,
    ) -> list[EvidenceRecord]:
        ...

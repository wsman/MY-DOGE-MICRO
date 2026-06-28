"""Repository port for extracted pages, chunks, and evidence records."""

from __future__ import annotations

from typing import Protocol

from doge.core.domain.chunk_models import DocumentChunk
from doge.core.domain.evidence_chunk_models import EvidenceChunk
from doge.core.domain.evidence_models import EvidenceRecord
from doge.core.domain.page_models import DocumentPage
from doge.shared.scope import TenantScope


class IEvidenceRepository(Protocol):
    """Persist and retrieve the document evidence chain."""

    def save_page(self, page: DocumentPage, scope: TenantScope) -> None:
        ...

    def list_pages(self, document_id: str, scope: TenantScope) -> list[DocumentPage]:
        ...

    def save_chunk(self, chunk: DocumentChunk, scope: TenantScope) -> None:
        ...

    def list_chunks(
        self,
        scope: TenantScope,
        document_ids: list[str] | None = None,
        limit: int = 20,
    ) -> list[DocumentChunk]:
        ...

    def get_chunk(self, chunk_id: str, scope: TenantScope) -> DocumentChunk | None:
        """Retrieve a single chunk by its chunk_id."""
        ...

    def list_chunks_for_run(self, run_id: str, scope: TenantScope) -> list[DocumentChunk]:
        """List all chunks associated with a given run_id via evidence records."""
        ...

    def save_evidence(self, evidence: EvidenceRecord, scope: TenantScope) -> None:
        ...

    def get_evidence(self, evidence_id: str, scope: TenantScope) -> EvidenceRecord | None:
        ...

    def list_evidence(
        self,
        *,
        scope: TenantScope,
        run_id: str | None = None,
        document_id: str | None = None,
        limit: int = 20,
    ) -> list[EvidenceRecord]:
        ...

    def list_evidence_chunks(
        self,
        *,
        scope: TenantScope,
        run_id: str | None = None,
        evidence_ids: list[str] | None = None,
        limit: int = 100,
    ) -> list[EvidenceChunk]:
        """Return evidence chunks for a run or a specific set of evidence IDs."""
        ...

    def get_evidence_batch(
        self,
        evidence_ids: list[str],
        scope: TenantScope,
    ) -> list[EvidenceRecord]:
        """Return all requested evidence records that exist and are accessible."""
        ...

"""Contract tests for persisted document repository boundaries."""

from __future__ import annotations

from doge.core.domain.document_models import Document, DocumentStatus
from doge.infrastructure.database.agent_repositories import SQLiteDocumentRepository
from doge.shared.scope import TenantScope


def test_document_store_persists_metadata_and_tenant_scope(tmp_path) -> None:
    db = tmp_path / "agent_state.db"
    repo = SQLiteDocumentRepository(db)
    tenant_a = TenantScope.enterprise("tenant-a", subject_hash="u-a")
    tenant_b = TenantScope.enterprise("tenant-b", subject_hash="u-b")
    document = Document.create(
        original_filename="market_summary_2026Q2.pdf",
        file_hash="hash-market-summary",
        mime_type="application/pdf",
        size_bytes=2048,
        storage_path=str(tmp_path / "market_summary_2026Q2.pdf"),
        parsing_status=DocumentStatus.UPLOADED,
    )

    repo.save(document, tenant_a)

    saved = repo.get(document.document_id, tenant_a)
    assert saved is not None
    assert saved["original_filename"] == "market_summary_2026Q2.pdf"
    assert saved["file_hash"] == "hash-market-summary"
    assert saved["parsing_status"] == "uploaded"
    assert repo.get(document.document_id, tenant_b) is None
    assert repo.list_recent(tenant_b) == []

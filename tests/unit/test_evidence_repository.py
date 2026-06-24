import pytest

from doge.core.domain.agent_models import AgentRun
from doge.core.domain.enterprise_context import IdentitySnapshot
from doge.core.domain.evidence_models import EvidenceRecord
from doge.core.domain.page_models import DocumentPage
from doge.application.services.page_extraction_service import ChunkingService
from doge.infrastructure.database.agent_repositories import SQLiteDocumentRepository, SQLiteRunRepository
from doge.infrastructure.database.evidence_repository import SQLiteEvidenceRepository


def test_evidence_repository_persists_pages_chunks_and_evidence(tmp_path):
    repository = SQLiteEvidenceRepository(tmp_path / "agent_state.db")
    page = DocumentPage.create(
        document_id="doc-1",
        page_number=1,
        text="Operating margin expanded by 2 points.",
        source_hash="hash-1",
    )
    chunk = ChunkingService().chunk_page(page)[0]
    evidence = EvidenceRecord.create(
        chunk=chunk,
        claim="margin expanded",
        support_snippet="Operating margin expanded",
        run_id="run-1",
        relevance_score=0.9,
        metadata={"source": "unit-test"},
    )

    repository.save_page(page)
    repository.save_chunk(chunk)
    repository.save_evidence(evidence)

    assert repository.list_pages("doc-1") == [page]
    assert repository.list_chunks(["doc-1"], limit=5) == [chunk]
    assert repository.get_evidence(evidence.evidence_id) == evidence
    assert repository.list_evidence(run_id="run-1") == [evidence]
    assert repository.list_evidence(document_id="doc-1") == [evidence]


def test_evidence_repository_filters_pages_chunks_and_evidence_by_tenant(tmp_path):
    repository = SQLiteEvidenceRepository(tmp_path / "agent_state.db")
    page_a = DocumentPage.create(
        document_id="doc-a",
        page_number=1,
        text="Tenant A margin expanded.",
        source_hash="hash-a",
    )
    page_b = DocumentPage.create(
        document_id="doc-b",
        page_number=1,
        text="Tenant B revenue declined.",
        source_hash="hash-b",
    )
    chunk_a = ChunkingService().chunk_page(page_a)[0]
    chunk_b = ChunkingService().chunk_page(page_b)[0]
    evidence_a = EvidenceRecord.create(
        chunk=chunk_a,
        claim="a",
        support_snippet="Tenant A margin",
        run_id="run-a",
    )
    evidence_b = EvidenceRecord.create(
        chunk=chunk_b,
        claim="b",
        support_snippet="Tenant B revenue",
        run_id="run-b",
    )

    repository.save_page(page_a, tenant_id="tenant-a")
    repository.save_chunk(chunk_a, tenant_id="tenant-a")
    repository.save_evidence(evidence_a, tenant_id="tenant-a")
    repository.save_page(page_b, tenant_id="tenant-b")
    repository.save_chunk(chunk_b, tenant_id="tenant-b")
    repository.save_evidence(evidence_b, tenant_id="tenant-b")

    assert repository.list_pages("doc-a", tenant_id="tenant-a") == [page_a]
    assert repository.list_pages("doc-b", tenant_id="tenant-a") == []
    assert repository.list_chunks(limit=10, tenant_id="tenant-a") == [chunk_a]
    assert repository.list_chunks(["doc-b"], limit=10, tenant_id="tenant-a") == []
    assert repository.get_evidence(evidence_a.evidence_id, tenant_id="tenant-a") == evidence_a
    assert repository.get_evidence(evidence_b.evidence_id, tenant_id="tenant-a") is None
    assert repository.list_evidence(run_id="run-a", tenant_id="tenant-a") == [evidence_a]
    assert repository.list_evidence(document_id="doc-b", tenant_id="tenant-a") == []


def test_evidence_repository_rejects_cross_tenant_parent_mismatch(tmp_path):
    db = tmp_path / "agent_state.db"
    documents = SQLiteDocumentRepository(db)
    runs = SQLiteRunRepository(db)
    repository = SQLiteEvidenceRepository(db)
    documents.save({"document_id": "doc-a", "tenant_id": "tenant-a", "filename": "a.txt", "content": "alpha"})
    run = AgentRun.create(
        workflow="investment_research",
        question="q",
        identity_snapshot=IdentitySnapshot(tenant_id="tenant-a", user_hash="user-a"),
    )
    runs.save(run)
    page = DocumentPage.create(document_id="doc-a", page_number=1, text="Tenant A text.")
    chunk = ChunkingService().chunk_page(page)[0]
    evidence = EvidenceRecord.create(
        chunk=chunk,
        claim="a",
        support_snippet="Tenant A",
        run_id=run.run_id,
    )

    with pytest.raises(ValueError, match="tenant mismatch"):
        repository.save_page(page, tenant_id="tenant-b")
    with pytest.raises(ValueError, match="tenant mismatch"):
        repository.save_evidence(evidence, tenant_id="tenant-b")

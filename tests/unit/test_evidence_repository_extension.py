"""Unit tests for IEvidenceRepository extensions (get_chunk, list_chunks_for_run)."""

import pytest

from doge.core.domain.agent_models import AgentRun
from doge.core.domain.enterprise_context import IdentitySnapshot
from doge.core.domain.evidence_models import EvidenceRecord
from doge.core.domain.page_models import DocumentPage
from doge.application.services.page_extraction_service import ChunkingService
from doge.infrastructure.database.agent_repositories import SQLiteDocumentRepository, SQLiteRunRepository
from doge.infrastructure.database.evidence_repository import SQLiteEvidenceRepository
from doge.shared.scope import TenantScope


def test_repository_get_chunk_retrieves_by_chunk_id(tmp_path):
    """get_chunk should return the correct chunk by chunk_id."""
    repository = SQLiteEvidenceRepository(tmp_path / "agent_state.db")
    page = DocumentPage.create(
        document_id="doc-1",
        page_number=1,
        text="Operating margin expanded by 2 points.",
        source_hash="hash-1",
    )
    chunk = ChunkingService().chunk_page(page)[0]
    repository.save_page(page)
    repository.save_chunk(chunk)

    retrieved = repository.get_chunk(chunk.chunk_id)
    assert retrieved == chunk


def test_repository_get_chunk_returns_none_for_missing(tmp_path):
    """get_chunk should return None when the chunk_id does not exist."""
    repository = SQLiteEvidenceRepository(tmp_path / "agent_state.db")
    assert repository.get_chunk("nonexistent-chunk-id") is None


def test_repository_get_chunk_respects_tenant(tmp_path):
    """get_chunk should enforce tenant isolation."""
    repository = SQLiteEvidenceRepository(tmp_path / "agent_state.db")
    page = DocumentPage.create(
        document_id="doc-1",
        page_number=1,
        text="Operating margin expanded.",
        source_hash="hash-1",
    )
    chunk = ChunkingService().chunk_page(page)[0]
    repository.save_page(page, tenant_id="tenant-a")
    repository.save_chunk(chunk, tenant_id="tenant-a")

    assert repository.get_chunk(chunk.chunk_id, tenant_id="tenant-a") == chunk
    assert repository.get_chunk(chunk.chunk_id, tenant_id="tenant-b") is None


def test_repository_list_chunks_for_run_returns_chunks_via_evidence(tmp_path):
    """list_chunks_for_run should return chunks linked to a run through evidence records."""
    db = tmp_path / "agent_state.db"
    documents = SQLiteDocumentRepository(db)
    runs = SQLiteRunRepository(db)
    repository = SQLiteEvidenceRepository(db)

    documents.save({"document_id": "doc-1", "tenant_id": "local", "filename": "a.txt", "content": "alpha"})
    run = AgentRun.create(
        workflow="investment_research",
        question="q",
        identity_snapshot=IdentitySnapshot(tenant_id="local", user_hash="user-a"),
    )
    runs.save(run)

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
        run_id=run.run_id,
    )

    repository.save_page(page)
    repository.save_chunk(chunk)
    repository.save_evidence(evidence)

    chunks = repository.list_chunks_for_run(run.run_id)
    assert len(chunks) == 1
    assert chunks[0] == chunk


def test_repository_list_chunks_for_run_returns_empty_for_unknown_run(tmp_path):
    """list_chunks_for_run should return an empty list for a non-existent run_id."""
    repository = SQLiteEvidenceRepository(tmp_path / "agent_state.db")
    assert repository.list_chunks_for_run("nonexistent-run-id") == []


def test_repository_list_chunks_for_run_respects_tenant(tmp_path):
    """list_chunks_for_run should enforce tenant isolation."""
    db = tmp_path / "agent_state.db"
    documents = SQLiteDocumentRepository(db)
    runs = SQLiteRunRepository(db)
    repository = SQLiteEvidenceRepository(db)

    documents.save({"document_id": "doc-a", "tenant_id": "tenant-a", "filename": "a.txt", "content": "alpha"})
    documents.save({"document_id": "doc-b", "tenant_id": "tenant-b", "filename": "b.txt", "content": "beta"})

    run_a = AgentRun.create(
        workflow="investment_research",
        question="q",
        identity_snapshot=IdentitySnapshot(tenant_id="tenant-a", user_hash="user-a"),
    )
    run_b = AgentRun.create(
        workflow="investment_research",
        question="q",
        identity_snapshot=IdentitySnapshot(tenant_id="tenant-b", user_hash="user-b"),
    )
    runs.save(run_a)
    runs.save(run_b)

    page_a = DocumentPage.create(document_id="doc-a", page_number=1, text="Tenant A text.", source_hash="hash-a")
    page_b = DocumentPage.create(document_id="doc-b", page_number=1, text="Tenant B text.", source_hash="hash-b")
    chunk_a = ChunkingService().chunk_page(page_a)[0]
    chunk_b = ChunkingService().chunk_page(page_b)[0]
    evidence_a = EvidenceRecord.create(chunk=chunk_a, claim="a", support_snippet="Tenant A", run_id=run_a.run_id)
    evidence_b = EvidenceRecord.create(chunk=chunk_b, claim="b", support_snippet="Tenant B", run_id=run_b.run_id)

    repository.save_page(page_a, tenant_id="tenant-a")
    repository.save_chunk(chunk_a, tenant_id="tenant-a")
    repository.save_evidence(evidence_a, tenant_id="tenant-a")
    repository.save_page(page_b, tenant_id="tenant-b")
    repository.save_chunk(chunk_b, tenant_id="tenant-b")
    repository.save_evidence(evidence_b, tenant_id="tenant-b")

    assert repository.list_chunks_for_run(run_a.run_id, tenant_id="tenant-a") == [chunk_a]
    assert repository.list_chunks_for_run(run_a.run_id, tenant_id="tenant-b") == []
    assert repository.list_chunks_for_run(run_b.run_id, tenant_id="tenant-b") == [chunk_b]


def test_repository_list_chunks_for_run_with_tenant_scope(tmp_path):
    """list_chunks_for_run should accept TenantScope for tenant isolation."""
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

    page = DocumentPage.create(document_id="doc-a", page_number=1, text="Tenant A text.", source_hash="hash-a")
    chunk = ChunkingService().chunk_page(page)[0]
    evidence = EvidenceRecord.create(chunk=chunk, claim="a", support_snippet="Tenant A", run_id=run.run_id)

    scope = TenantScope.enterprise("tenant-a", "user-a")
    repository.save_page(page, scope)
    repository.save_chunk(chunk, scope)
    repository.save_evidence(evidence, scope)

    assert repository.list_chunks_for_run(run.run_id, scope) == [chunk]
    other_scope = TenantScope.enterprise("tenant-b", "user-b")
    assert repository.list_chunks_for_run(run.run_id, other_scope) == []


def test_repository_list_chunks_for_run_multiple_chunks_same_run(tmp_path):
    """list_chunks_for_run should return multiple chunks linked to the same run."""
    db = tmp_path / "agent_state.db"
    documents = SQLiteDocumentRepository(db)
    runs = SQLiteRunRepository(db)
    repository = SQLiteEvidenceRepository(db)

    documents.save({"document_id": "doc-1", "tenant_id": "local", "filename": "a.txt", "content": "alpha"})
    run = AgentRun.create(
        workflow="investment_research",
        question="q",
        identity_snapshot=IdentitySnapshot(tenant_id="local", user_hash="user-a"),
    )
    runs.save(run)

    page1 = DocumentPage.create(document_id="doc-1", page_number=1, text="Page one content.", source_hash="hash-1")
    page2 = DocumentPage.create(document_id="doc-1", page_number=2, text="Page two content.", source_hash="hash-2")
    chunk1 = ChunkingService().chunk_page(page1)[0]
    chunk2 = ChunkingService().chunk_page(page2)[0]
    evidence1 = EvidenceRecord.create(chunk=chunk1, claim="c1", support_snippet="Page one", run_id=run.run_id)
    evidence2 = EvidenceRecord.create(chunk=chunk2, claim="c2", support_snippet="Page two", run_id=run.run_id)

    repository.save_page(page1)
    repository.save_page(page2)
    repository.save_chunk(chunk1)
    repository.save_chunk(chunk2)
    repository.save_evidence(evidence1)
    repository.save_evidence(evidence2)

    chunks = repository.list_chunks_for_run(run.run_id)
    assert len(chunks) == 2
    assert chunk1 in chunks
    assert chunk2 in chunks

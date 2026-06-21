from doge.core.domain.evidence_models import EvidenceRecord
from doge.core.domain.page_models import DocumentPage
from doge.application.services.page_extraction_service import ChunkingService
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

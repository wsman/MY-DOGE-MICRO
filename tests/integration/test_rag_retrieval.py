from doge.application.services.page_extraction_service import PageExtractionService
from doge.application.services.rag_service import RAGService
from doge.core.domain.document_models import Document, DocumentStatus
from doge.infrastructure.database.embedding_cache import SQLiteEmbeddingCache
from doge.infrastructure.database.evidence_repository import SQLiteEvidenceRepository
from doge.infrastructure.llm.embedding_client import HashingEmbeddingProvider
from doge.infrastructure.vector.sqlite_store import SQLiteVectorStore


def test_rag_service_retrieves_source_chunk_metadata(tmp_path):
    db = tmp_path / "agent_state.db"
    evidence = SQLiteEvidenceRepository(db)
    document = Document.create(
        document_id="doc-semi",
        original_filename="industry.md",
        file_hash="hash-semi",
        parsing_status=DocumentStatus.PARSED,
        content="Semiconductor outlook improved as AI demand accelerated.",
    )
    PageExtractionService(evidence_repository=evidence).extract(document)
    service = RAGService(
        evidence_repository=evidence,
        embedding_provider=HashingEmbeddingProvider(),
        vector_store=SQLiteVectorStore(db),
        embedding_cache=SQLiteEmbeddingCache(db),
    )

    result = service.search("semiconductor outlook", limit=1)

    assert result["results"][0]["document_id"] == "doc-semi"
    assert result["results"][0]["page_number"] == 1
    assert result["results"][0]["chunk_id"].startswith("chk-")
    assert result["results"][0]["visibility"] == "local"

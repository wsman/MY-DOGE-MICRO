import asyncio
import hashlib
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor

from doge.application.services.file_upload_service import FileUploadService
from doge.application.services.page_extraction_service import PageExtractionService
from doge.application.services.rag_service import RAGService
from doge.core.domain.agent_models import AgentSession
from doge.infrastructure.database.agent_repositories import SQLiteDocumentRepository, SQLiteSessionRepository
from doge.infrastructure.database.embedding_cache import SQLiteEmbeddingCache
from doge.infrastructure.database.evidence_repository import SQLiteEvidenceRepository
from doge.infrastructure.database.sqlite_uow import SQLiteAgentUnitOfWork
from doge.infrastructure.llm.embedding_client import HashingEmbeddingProvider
from doge.infrastructure.vector.sqlite_store import SQLiteVectorStore


class _TextParser:
    def parse(self, path, *, max_chars=12000):
        return path.read_text(encoding="utf-8")[:max_chars]


def test_s015_document_ingestion_throughput_smoke(tmp_path):
    db = tmp_path / "agent_state.db"
    evidence = SQLiteEvidenceRepository(db)
    service = FileUploadService(
        SQLiteDocumentRepository(db),
        storage_dir=tmp_path / "documents",
        parser=_TextParser(),
        extraction_service=PageExtractionService(evidence_repository=evidence),
    )

    start = time.perf_counter()
    for index in range(12):
        payload = (
            f"# Semiconductor Evidence {index}\n"
            "AI accelerator demand and inventory digestion are cited in this sprint evidence.\n"
        ).encode("utf-8")
        service.register_bytes(filename=f"evidence-{index}.md", payload=payload)
    elapsed = time.perf_counter() - start

    assert elapsed < 3.0
    assert len(SQLiteDocumentRepository(db).list_recent(limit=20)) == 12
    assert len(evidence.list_chunks(limit=20)) == 12


def test_s015_rag_latency_and_embedding_cache_smoke(tmp_path):
    db = tmp_path / "agent_state.db"
    evidence = SQLiteEvidenceRepository(db)
    upload = FileUploadService(
        SQLiteDocumentRepository(db),
        storage_dir=tmp_path / "documents",
        parser=_TextParser(),
        extraction_service=PageExtractionService(evidence_repository=evidence),
    )
    document = upload.register_text(
        filename="semiconductor.md",
        content="Semiconductor outlook improved as AI demand accelerated and capex remained disciplined.",
        document_id="doc-semi",
    )
    service = RAGService(
        evidence_repository=evidence,
        embedding_provider=HashingEmbeddingProvider(dimensions=32),
        vector_store=SQLiteVectorStore(db),
        embedding_cache=SQLiteEmbeddingCache(db),
    )

    start = time.perf_counter()
    result = service.search("semiconductor AI demand", document_ids=[document["document_id"]], limit=1)
    elapsed = time.perf_counter() - start

    chunk = evidence.list_chunks([document["document_id"]], limit=1)[0]
    cache_key = hashlib.sha256(chunk.text.encode("utf-8")).hexdigest()
    query_key = hashlib.sha256("semiconductor AI demand".encode("utf-8")).hexdigest()
    cache = SQLiteEmbeddingCache(db)

    assert elapsed < 2.0
    assert result["results"][0]["chunk_id"] == chunk.chunk_id
    assert cache.get(cache_key) is not None
    assert cache.get(query_key) is not None


def test_s015_concurrent_enqueue_smoke_budget(tmp_path):
    db = tmp_path / "agent_state.db"
    session = AgentSession.create("S015 concurrent run smoke")
    SQLiteSessionRepository(db).save(session)

    def enqueue_once(index: int) -> str:
        return asyncio.run(
            SQLiteAgentUnitOfWork(db).enqueue_run_and_turn(
                session_id=session.session_id,
                message=f"Analyze semiconductor run {index}",
                idempotency_key=f"s015-{index}",
            )
        )

    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=6) as executor:
        run_ids = list(executor.map(enqueue_once, range(12)))
    elapsed = time.perf_counter() - start

    with sqlite3.connect(str(db)) as conn:
        run_count = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        queue_count = conn.execute("SELECT COUNT(*) FROM run_queue").fetchone()[0]

    assert elapsed < 5.0
    assert len(set(run_ids)) == 12
    assert run_count == 12
    assert queue_count == 12

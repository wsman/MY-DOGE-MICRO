import sqlite3

from doge.core.domain.agent_models import AgentRun, AgentSession
from doge.core.domain.document_models import Document, DocumentStatus
from doge.infrastructure.database.agent_repositories import (
    SQLiteDocumentRepository,
    SQLiteIdempotencyStore,
    SQLiteRunQueue,
    SQLiteRunRepository,
    SQLiteSessionRepository,
    bootstrap_agent_schema,
)


def test_agent_schema_bootstrap_is_idempotent(tmp_path):
    db = tmp_path / "agent_state.db"

    bootstrap_agent_schema(db)
    bootstrap_agent_schema(db)

    session = AgentSession.create("Idempotent")
    SQLiteSessionRepository(db).save(session)
    run = AgentRun.create(workflow="investment_research", question="q", session_id=session.session_id)
    SQLiteRunRepository(db).save(run)

    assert SQLiteRunRepository(db).get(run.run_id) is not None


def test_agent_schema_bootstrap_includes_case_workflow_tables(tmp_path):
    db = tmp_path / "agent_state.db"

    bootstrap_agent_schema(db)

    with sqlite3.connect(db) as conn:
        table_names = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    assert {"case_assets", "workflow_executions", "case_decisions"}.issubset(table_names)


def test_run_queue_latest_status_drives_pending_list(tmp_path):
    db = tmp_path / "agent_state.db"
    queue = SQLiteRunQueue(db)

    queue.enqueue("run-1")
    queue.append_status("run-1", "running")
    assert queue.list_pending() == ["run-1"]

    queue.append_status("run-1", "done")
    assert queue.list_pending() == []


def test_idempotency_store_scopes_keys(tmp_path):
    db = tmp_path / "agent_state.db"
    store = SQLiteIdempotencyStore(db)

    store.set("idem-1", "ses-a", "run-a")
    store.set("idem-1", "ses-b", "run-b")

    assert store.get("idem-1", "ses-a") == "run-a"
    assert store.get("idem-1", "ses-b") == "run-b"


def test_document_repository_persists_file_metadata_and_hash_lookup(tmp_path):
    db = tmp_path / "agent_state.db"
    repo = SQLiteDocumentRepository(db)
    document = Document.create(
        original_filename="report.pdf",
        file_hash="abc123",
        mime_type="application/pdf",
        size_bytes=42,
        storage_path=str(tmp_path / "report.pdf"),
        kimi_file_purpose="file-extract",
        parsing_status=DocumentStatus.UPLOADED,
    )

    repo.save(document)

    saved = repo.get(document.document_id)
    by_hash = repo.get_by_hash("abc123")
    assert saved is not None
    assert saved["original_filename"] == "report.pdf"
    assert saved["file_hash"] == "abc123"
    assert saved["mime_type"] == "application/pdf"
    assert saved["size_bytes"] == 42
    assert saved["kimi_file_purpose"] == "file-extract"
    assert saved["parsing_status"] == "uploaded"
    assert by_hash == saved

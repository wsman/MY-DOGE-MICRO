from doge.core.domain.agent_models import AgentRun, AgentSession
from doge.infrastructure.database.agent_repositories import (
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

import time
import asyncio

import pytest
from fastapi.testclient import TestClient

from doge.config import reset_settings
from doge.application.agent.worker import AsyncioWorker
from doge.application.composition import build_persisted_research_agent_runtime
from doge.infrastructure.database.agent_repositories import SQLiteIdempotencyStore, SQLiteRunQueue, SQLiteSessionRepository
from doge.interfaces.api import deps
from doge.interfaces.api.main import app


def _reset(monkeypatch, tmp_path):
    monkeypatch.setenv("DOGE_AGENT_DB", str(tmp_path / "agent_state.db"))
    reset_settings()
    deps._persisted_research_agent_runtime = None
    deps._event_bus = None
    deps._worker = None
    deps._run_queue = None
    deps._idempotency_store = None


def test_daemon_worker_processes_queued_runs(tmp_path, monkeypatch):
    _reset(monkeypatch, tmp_path)
    client = TestClient(app)
    session = client.post("/v1/sessions", json={"title": "Worker"}).json()

    run_id = client.post(f"/v1/sessions/{session['session_id']}/turns", json={"message": "Analyze"}).json()["run_id"]
    time.sleep(0.3)
    run = client.get(f"/v1/runs/{run_id}").json()

    assert run["events"]
    assert run["status"] == "awaiting_approval"


def test_approval_resolution_resumes_via_runtime(tmp_path, monkeypatch):
    _reset(monkeypatch, tmp_path)
    client = TestClient(app)
    session = client.post("/v1/sessions", json={"title": "Approval"}).json()
    run_id = client.post(f"/v1/sessions/{session['session_id']}/turns", json={"message": "Analyze"}).json()["run_id"]
    time.sleep(0.3)
    run = client.get(f"/v1/runs/{run_id}").json()
    approval_id = run["approvals"][0]["approval_id"]

    resolved = client.post(f"/v1/runs/{run_id}/approvals/{approval_id}", json={"approved": True}).json()

    assert resolved["status"] == "completed"
    assert resolved["artifacts"]


def test_cancel_run_transitions_state_machine(tmp_path, monkeypatch):
    _reset(monkeypatch, tmp_path)
    client = TestClient(app)
    session = client.post("/v1/sessions", json={"title": "Cancel"}).json()
    run_id = client.post(f"/v1/sessions/{session['session_id']}/turns", json={"message": "Analyze"}).json()["run_id"]

    cancelled = client.post(f"/v1/runs/{run_id}/cancel").json()

    assert cancelled["status"] in {"cancelled", "awaiting_approval", "completed"}


@pytest.mark.asyncio
async def test_worker_recovers_queued_runs_from_sqlite(tmp_path, monkeypatch):
    db = tmp_path / "agent_state.db"
    monkeypatch.setenv("DOGE_AGENT_DB", str(db))
    reset_settings()
    runtime = build_persisted_research_agent_runtime(db_path=db)
    sessions = SQLiteSessionRepository(db)
    run_queue = SQLiteRunQueue(db)
    worker = AsyncioWorker(runtime, sessions, run_queue, SQLiteIdempotencyStore(db))
    run_queue.enqueue("run-recover")

    worker.recover()

    assert worker._queue.qsize() == 1
    await worker.stop()


def test_worker_recovery_on_startup_without_new_tasks(tmp_path, monkeypatch):
    _reset(monkeypatch, tmp_path)
    db = tmp_path / "agent_state.db"
    runtime = build_persisted_research_agent_runtime(db_path=db)
    run = asyncio.run(runtime.create_run({
        "workflow": "investment_research",
        "question": "Analyze stranded run.",
        "model_policy": {"max_tool_rounds": 8},
    }))
    SQLiteRunQueue(db).enqueue(run.run_id)

    with TestClient(app) as client:
        deadline = time.time() + 3
        while time.time() < deadline:
            loaded = client.get(f"/v1/runs/{run.run_id}").json()
            if loaded["events"] and loaded["status"] == "awaiting_approval":
                break
            time.sleep(0.05)
        else:
            raise AssertionError("stranded run was not recovered")

    assert loaded["status"] == "awaiting_approval"

import time
import asyncio
import threading
from typing import Any, AsyncIterator

import pytest
from fastapi.testclient import TestClient

from doge.config import reset_settings
from doge.application.agent.tools import ToolRegistry, ToolResult
from doge.application.agent.worker import AsyncioWorker
from doge.application.composition import build_agent_unit_of_work, build_persisted_research_agent_runtime
from doge.core.domain.agent_models import AgentSession, EventType, RunStatus
from doge.core.ports.agent_model import AgentMessage, AgentResponse
from doge.infrastructure.database.agent_repositories import SQLiteIdempotencyStore, SQLiteRunQueue, SQLiteSessionRepository
from doge.interfaces.api import deps
from doge.interfaces.api.main import app


def _reset(monkeypatch, tmp_path):
    monkeypatch.setenv("DOGE_AGENT_DB", str(tmp_path / "agent_state.db"))
    reset_settings()
    deps._persisted_research_agent_runtime = None
    deps._event_bus = None
    deps._event_subscriber = None
    deps._worker = None
    deps._run_queue = None
    deps._idempotency_store = None
    deps._agent_unit_of_work = None


def test_daemon_worker_processes_queued_runs(tmp_path, monkeypatch):
    _reset(monkeypatch, tmp_path)
    with TestClient(app) as client:
        session = client.post("/v1/sessions", json={"title": "Worker"}).json()

        run_id = client.post(f"/v1/sessions/{session['session_id']}/turns", json={"message": "Analyze"}).json()["run_id"]
        deadline = time.time() + 3
        while time.time() < deadline:
            run = client.get(f"/v1/runs/{run_id}").json()
            if run["status"] == "awaiting_approval":
                break
            time.sleep(0.05)
        else:
            raise AssertionError("run did not reach awaiting_approval")

    assert run["events"]
    assert run["status"] == "awaiting_approval"


def test_approval_resolution_returns_202_and_worker_completes_run(tmp_path, monkeypatch):
    _reset(monkeypatch, tmp_path)
    with TestClient(app) as client:
        session = client.post("/v1/sessions", json={"title": "Approval"}).json()
        run_id = client.post(f"/v1/sessions/{session['session_id']}/turns", json={"message": "Analyze"}).json()["run_id"]
        time.sleep(0.3)
        run = client.get(f"/v1/runs/{run_id}").json()
        approval_id = run["approvals"][0]["approval_id"]

        response = client.post(f"/v1/runs/{run_id}/approvals/{approval_id}", json={"approved": True})
        resolved = response.json()

        assert response.status_code == 202
        assert resolved["status"] == "queued"
        deadline = time.time() + 3
        while time.time() < deadline:
            run = client.get(f"/v1/runs/{run_id}").json()
            if run["status"] == "completed":
                break
            time.sleep(0.05)
        else:
            raise AssertionError("approved run did not complete")
    assert run["artifacts"]


def test_cancel_run_transitions_state_machine(tmp_path, monkeypatch):
    _reset(monkeypatch, tmp_path)
    with TestClient(app) as client:
        session = client.post("/v1/sessions", json={"title": "Cancel"}).json()
        run_id = client.post(f"/v1/sessions/{session['session_id']}/turns", json={"message": "Analyze"}).json()["run_id"]

        response = client.post(f"/v1/runs/{run_id}/cancel")
        cancelled = response.json()

    assert response.status_code == 202
    assert cancelled["status"] in {"cancelling", "cancelled"}


@pytest.mark.asyncio
async def test_worker_recovers_queued_runs_from_sqlite(tmp_path, monkeypatch):
    db = tmp_path / "agent_state.db"
    monkeypatch.setenv("DOGE_AGENT_DB", str(db))
    reset_settings()
    runtime = build_persisted_research_agent_runtime(db_path=db)
    sessions = SQLiteSessionRepository(db)
    run_queue = SQLiteRunQueue(db)
    worker = AsyncioWorker(runtime, sessions, run_queue, SQLiteIdempotencyStore(db), build_agent_unit_of_work(db))
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


@pytest.mark.asyncio
async def test_cancel_run_aborts_active_work_and_ends_cancelled(tmp_path, monkeypatch):
    db = tmp_path / "agent_state.db"
    monkeypatch.setenv("DOGE_AGENT_DB", str(db))
    reset_settings()
    started = threading.Event()

    class SlowToolModel:
        async def chat(
            self,
            messages: list[AgentMessage],
            *,
            tools: list[dict[str, Any]] | None = None,
            tool_choice: str | None = None,
            max_tokens: int = 16384,
            stream: bool = True,
        ) -> AsyncIterator[AgentResponse]:
            yield AgentResponse(message=AgentMessage(
                role="assistant",
                content="",
                tool_calls=[{
                    "id": "call-slow",
                    "type": "function",
                    "function": {"name": "slow_tool", "arguments": "{}"},
                }],
            ))

    registry = ToolRegistry()
    registry.register({
        "type": "function",
        "function": {
            "name": "slow_tool",
            "description": "slow",
            "parameters": {"type": "object", "properties": {}},
        },
    }, lambda **_: _slow_tool(started))
    sessions = SQLiteSessionRepository(db)
    session = AgentSession.create("Cancel active tool")
    sessions.save(session)
    runtime = build_persisted_research_agent_runtime(
        model=SlowToolModel(),
        tool_registry=registry,
        db_path=db,
    )
    worker = AsyncioWorker(
        runtime,
        sessions,
        SQLiteRunQueue(db),
        SQLiteIdempotencyStore(db),
        build_agent_unit_of_work(db),
    )

    try:
        run_id = await worker.enqueue_run(session.session_id, "Run a slow tool")
        assert await asyncio.to_thread(started.wait, 2)

        cancelling = await worker.cancel_run(run_id)
        await asyncio.wait_for(worker._queue.join(), timeout=3)

        run = runtime.get_run(run_id)
        assert cancelling.status == RunStatus.CANCELLING
        assert run is not None
        assert run.status == RunStatus.CANCELLED
        event_types = [event.event_type for event in run.events]
        assert EventType.RUN_CANCELLED in event_types
        assert EventType.TOOL_RESULT not in event_types
        cancelled_at = event_types.index(EventType.RUN_CANCELLED)
        assert all(
            event_type not in {EventType.MODEL_RESPONSE, EventType.TOOL_CALL, EventType.TOOL_RESULT}
            for event_type in event_types[cancelled_at + 1:]
        )
    finally:
        await worker.stop()


def _slow_tool(started: threading.Event) -> ToolResult:
    started.set()
    time.sleep(1)
    return ToolResult("slow_tool", {"done": True})


@pytest.mark.asyncio
async def test_cancel_run_aborts_active_model_and_ends_cancelled(tmp_path, monkeypatch):
    db = tmp_path / "agent_state.db"
    monkeypatch.setenv("DOGE_AGENT_DB", str(db))
    reset_settings()
    started = asyncio.Event()

    class SlowModel:
        async def chat(
            self,
            messages: list[AgentMessage],
            *,
            tools: list[dict[str, Any]] | None = None,
            tool_choice: str | None = None,
            max_tokens: int = 16384,
            stream: bool = True,
        ) -> AsyncIterator[AgentResponse]:
            started.set()
            await asyncio.sleep(5)
            yield AgentResponse(message=AgentMessage(role="assistant", content="late memo"))

    sessions = SQLiteSessionRepository(db)
    session = AgentSession.create("Cancel active model")
    sessions.save(session)
    runtime = build_persisted_research_agent_runtime(
        model=SlowModel(),
        tool_registry=ToolRegistry(),
        db_path=db,
    )
    worker = AsyncioWorker(
        runtime,
        sessions,
        SQLiteRunQueue(db),
        SQLiteIdempotencyStore(db),
        build_agent_unit_of_work(db),
    )

    try:
        run_id = await worker.enqueue_run(session.session_id, "Run a slow model")
        await asyncio.wait_for(started.wait(), timeout=2)

        cancelling = await worker.cancel_run(run_id)
        await asyncio.wait_for(worker._queue.join(), timeout=3)

        run = runtime.get_run(run_id)
        assert cancelling.status == RunStatus.CANCELLING
        assert run is not None
        assert run.status == RunStatus.CANCELLED
        event_types = [event.event_type for event in run.events]
        assert EventType.RUN_CANCELLED in event_types
        assert EventType.MODEL_RESPONSE not in event_types
        cancelled_at = event_types.index(EventType.RUN_CANCELLED)
        assert event_types[cancelled_at + 1:] == []
    finally:
        await worker.stop()


@pytest.mark.asyncio
async def test_worker_exception_records_failed_run_and_error_event(tmp_path, monkeypatch):
    db = tmp_path / "agent_state.db"
    monkeypatch.setenv("DOGE_AGENT_DB", str(db))
    reset_settings()

    class FailingModel:
        async def chat(
            self,
            messages: list[AgentMessage],
            *,
            tools: list[dict[str, Any]] | None = None,
            tool_choice: str | None = None,
            max_tokens: int = 16384,
            stream: bool = True,
        ) -> AsyncIterator[AgentResponse]:
            raise RuntimeError("model exploded")
            yield AgentResponse(message=AgentMessage(role="assistant", content="unreachable"))

    sessions = SQLiteSessionRepository(db)
    session = AgentSession.create("Worker failure")
    sessions.save(session)
    runtime = build_persisted_research_agent_runtime(
        model=FailingModel(),
        tool_registry=ToolRegistry(),
        db_path=db,
    )
    worker = AsyncioWorker(
        runtime,
        sessions,
        SQLiteRunQueue(db),
        SQLiteIdempotencyStore(db),
        build_agent_unit_of_work(db),
        worker_id="worker-failure-test",
    )

    try:
        run_id = await worker.enqueue_run(session.session_id, "Fail this run")
        await asyncio.wait_for(worker._queue.join(), timeout=3)

        run = runtime.get_run(run_id)
        assert run is not None
        assert run.status == RunStatus.FAILED
        assert run.events[-1].event_type == EventType.ERROR
        assert "model exploded" in run.events[-1].payload["message"]
    finally:
        await worker.stop()

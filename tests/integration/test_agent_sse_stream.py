import json
import threading
import time

from fastapi.testclient import TestClient

from doge.application.composition import build_research_agent_runtime
from doge.config import reset_settings
from doge.core.domain.agent_models import AgentEvent, AgentRun, EventType, RunStatus
from doge.infrastructure.database.agent_repositories import SQLiteEventRepository, SQLiteRunRepository
from doge.interfaces.api import deps
from doge.interfaces.api.main import app


def _reset_agent_deps(monkeypatch, tmp_path):
    monkeypatch.setenv("DOGE_AGENT_DB", str(tmp_path / "agent_state.db"))
    reset_settings()
    deps._research_agent_runtime = None
    deps._persisted_research_agent_runtime = None
    deps._event_bus = None
    deps._event_subscriber = None
    deps._worker = None
    deps._run_queue = None
    deps._idempotency_store = None
    deps._agent_unit_of_work = None


def _collect_data_events(response):
    events = []
    for line in response.iter_lines():
        if isinstance(line, bytes):
            line = line.decode("utf-8")
        if line.startswith("data: "):
            events.append(json.loads(line.removeprefix("data: ")))
    return events


def test_agent_sse_stream_returns_existing_events():
    runtime = build_research_agent_runtime()
    app.dependency_overrides[deps.get_research_agent_runtime] = lambda: runtime
    try:
        client = TestClient(app)
        created = client.post("/api/agent/runs", json={
            "question": "Analyze the company.",
            "model_policy": {"max_tool_rounds": 8},
        })
        run_id = created.json()["run_id"]
        with client.stream("GET", f"/api/agent/runs/{run_id}/stream") as resp:
            assert resp.status_code == 200
            events = _collect_data_events(resp)
    finally:
        app.dependency_overrides.clear()

    assert events
    assert events[0]["event_type"] == "run_created"


def _completed_v1_run(client):
    session = client.post("/v1/sessions", json={"title": "SSE"}).json()
    run_id = client.post(f"/v1/sessions/{session['session_id']}/turns", json={"message": "Analyze"}).json()["run_id"]
    deadline = time.time() + 3
    while time.time() < deadline:
        run = client.get(f"/v1/runs/{run_id}").json()
        if run["status"] == "awaiting_approval" and run["approvals"]:
            approval_id = run["approvals"][0]["approval_id"]
            client.post(f"/v1/runs/{run_id}/approvals/{approval_id}", json={"approved": True})
            break
        time.sleep(0.05)
    deadline = time.time() + 3
    while time.time() < deadline:
        run = client.get(f"/v1/runs/{run_id}").json()
        if run["status"] == "completed":
            return run_id
        time.sleep(0.05)
    raise AssertionError("run did not complete")


def test_sse_stream_replays_all_events_for_completed_run(tmp_path, monkeypatch):
    _reset_agent_deps(monkeypatch, tmp_path)
    with TestClient(app) as client:
        run_id = _completed_v1_run(client)
        with client.stream("GET", f"/v1/runs/{run_id}/stream") as resp:
            assert resp.status_code == 200
            events = _collect_data_events(resp)

    event_types = {event["event_type"] for event in events}
    assert {"run_created", "model_response", "tool_call", "tool_result", "artifact_created"} <= event_types
    assert len(events) > 1


def test_sse_stream_completed_run_with_last_event_id_replays_from_checkpoint(tmp_path, monkeypatch):
    _reset_agent_deps(monkeypatch, tmp_path)
    with TestClient(app) as client:
        run_id = _completed_v1_run(client)
        all_events = client.get(f"/v1/runs/{run_id}/events").json()["events"]
        checkpoint = all_events[1]["sequence"]
        with client.stream(
            "GET",
            f"/v1/runs/{run_id}/stream",
            headers={"Last-Event-ID": str(checkpoint)},
        ) as resp:
            assert resp.status_code == 200
            events = _collect_data_events(resp)

    assert events
    assert all(event["sequence"] > checkpoint for event in events)
    assert len(events) == len([event for event in all_events if event["sequence"] > checkpoint])


def test_sse_stream_live_run_closes_after_terminal_event(tmp_path, monkeypatch):
    _reset_agent_deps(monkeypatch, tmp_path)
    with TestClient(app) as client:
        session = client.post("/v1/sessions", json={"title": "Live SSE"}).json()
        run_id = client.post(f"/v1/sessions/{session['session_id']}/turns", json={"message": "Analyze"}).json()["run_id"]
        with client.stream("GET", f"/v1/runs/{run_id}/stream") as resp:
            assert resp.status_code == 200
            events = _collect_data_events(resp)

    assert events
    assert events[-1]["event_type"] in {"approval_requested", "artifact_created", "error", "run_cancelled"}


def test_v1_stream_receives_sqlite_events_without_event_bus_publish(tmp_path, monkeypatch):
    _reset_agent_deps(monkeypatch, tmp_path)
    db = tmp_path / "agent_state.db"
    runs = SQLiteRunRepository(db)
    events = SQLiteEventRepository(db)
    run = AgentRun.create(workflow="investment_research", question="Separate process", run_id="run-cross-process")
    run.status = RunStatus.RUNNING
    runs.save(run)

    def complete_from_separate_repository():
        time.sleep(0.05)
        loaded = runs.get(run.run_id)
        assert loaded is not None
        loaded.status = RunStatus.COMPLETED
        runs.save(loaded)
        events.append(AgentEvent(
            event_id="evt-cross-process-terminal",
            run_id=run.run_id,
            event_type=EventType.ARTIFACT_CREATED,
            payload={"artifact_id": "art-cross-process", "kind": "memo", "title": "Memo"},
        ))

    writer = threading.Thread(target=complete_from_separate_repository)
    writer.start()
    try:
        with TestClient(app) as client:
            with client.stream("GET", f"/v1/runs/{run.run_id}/stream") as resp:
                assert resp.status_code == 200
                streamed = _collect_data_events(resp)
    finally:
        writer.join(timeout=1)

    assert [event["event_type"] for event in streamed] == ["artifact_created"]

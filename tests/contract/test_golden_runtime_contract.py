"""Golden observable runtime contract across v1 and Python SDK surfaces."""

from __future__ import annotations

import json
import time

import httpx
from fastapi.testclient import TestClient

from doge.config import reset_settings
from doge.interfaces.api import deps
from doge.interfaces.api.main import app
from doge_sdk import DogeClient


def test_golden_runtime_contract_matches_v1_and_python_sdk(tmp_path, monkeypatch):
    _reset_agent_deps(monkeypatch, tmp_path)
    with TestClient(app) as client:
        session = client.post("/v1/sessions", json={"title": "Golden"}).json()
        run_id = client.post(
            f"/v1/sessions/{session['session_id']}/turns",
            json={"message": "Analyze AAPL"},
        ).json()["run_id"]
        run = _wait_for_run(client, run_id, {"awaiting_approval"})
        events = client.get(f"/v1/runs/{run_id}/events").json()["events"]
        approval_id = run["approvals"][0]["approval_id"]
        approval = client.post(
            f"/v1/runs/{run_id}/approvals/{approval_id}",
            json={"approved": True},
        ).json()
        _wait_for_run(client, run_id, {"completed"})
        with client.stream("GET", f"/v1/runs/{run_id}/stream") as response:
            stream_body = response.read().decode("utf-8")

        cancel_run_id = client.post(
            f"/v1/sessions/{session['session_id']}/turns",
            json={"message": "Cancel me"},
        ).json()["run_id"]
        cancel = client.post(f"/v1/runs/{cancel_run_id}/cancel").json()

    api_contract = _normalize_contract(
        session_id=session["session_id"],
        run_id=run_id,
        events=events,
        approval_status=approval["status"],
        cancel_status=cancel["status"],
        stream_events=_parse_sse(stream_body),
    )

    sdk = DogeClient(
        base_url="http://testserver",
        transport=httpx.MockTransport(
            _sdk_handler(
                session=session,
                run_id=run_id,
                approval_id=approval_id,
                events=events,
                approval=approval,
                cancel=cancel,
                stream_body=stream_body,
            )
        ),
    )
    sdk_session = sdk.sessions.create("Golden")
    sdk_run_id = sdk_session.create_turn("Analyze AAPL")
    sdk_events = sdk.runs.events(sdk_run_id)
    sdk_approval = sdk.runs.approve(sdk_run_id, approval_id)
    sdk_cancel = sdk.runs.cancel(cancel_run_id)
    sdk_stream_events = list(sdk.runs.stream(sdk_run_id))

    sdk_contract = _normalize_contract(
        session_id=sdk_session.session_id,
        run_id=sdk_run_id,
        events=sdk_events,
        approval_status=sdk_approval["status"],
        cancel_status=sdk_cancel["status"],
        stream_events=[{"id": event.id, "event": event.type} for event in sdk_stream_events],
    )

    assert sdk_contract == api_contract


def test_golden_runtime_contract_explicit_resume_path(tmp_path, monkeypatch):
    _reset_agent_deps(monkeypatch, tmp_path)
    with TestClient(app) as client:
        session = client.post("/v1/sessions", json={"title": "Golden Resume"}).json()
        run_id = client.post(
            f"/v1/sessions/{session['session_id']}/turns",
            json={"message": "Analyze AAPL"},
        ).json()["run_id"]
        run = _wait_for_run(client, run_id, {"awaiting_approval"})
        approval_id = run["approvals"][0]["approval_id"]

        resumed = client.post(
            f"/v1/runs/{run_id}/resume",
            json={"approval_id": approval_id, "approved": True},
        ).json()

    assert resumed["status"] == "completed"
    sdk = DogeClient(
        base_url="http://testserver",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(202, json=resumed)
            if request.url.path == f"/v1/runs/{run_id}/resume"
            else httpx.Response(404, json={"error": {"message": "not found"}})
        ),
    )

    sdk_resumed = sdk.runs.resume(run_id, approval_id=approval_id)

    assert sdk_resumed["run_id"] == run_id
    assert sdk_resumed["status"] == "completed"


def _reset_agent_deps(monkeypatch, tmp_path):
    monkeypatch.delenv("DOGE_PROCESS_ROLE", raising=False)
    monkeypatch.setenv("DOGE_AGENT_DB", str(tmp_path / "agent_state.db"))
    monkeypatch.setenv("DOGE_DOCUMENT_STORAGE_DIR", str(tmp_path / "documents"))
    reset_settings()
    deps._persisted_research_agent_runtime = None
    deps._event_bus = None
    deps._event_subscriber = None
    deps._worker = None
    deps._run_queue = None
    deps._idempotency_store = None
    deps._agent_unit_of_work = None
    deps._runtime_outbox_publisher = None
    deps._file_upload_service = None
    deps._enterprise_governance_repository = None


def _wait_for_run(client: TestClient, run_id: str, statuses: set[str], timeout: float = 4.0) -> dict:
    deadline = time.monotonic() + timeout
    body = {}
    while time.monotonic() < deadline:
        response = client.get(f"/v1/runs/{run_id}")
        assert response.status_code == 200
        body = response.json()
        if body["status"] in statuses:
            return body
        time.sleep(0.1)
    assert body.get("status") in statuses
    return body


def _sdk_handler(*, session, run_id, approval_id, events, approval, cancel, stream_body):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/sessions" and request.method == "POST":
            return httpx.Response(200, json=session)
        if request.url.path == f"/v1/sessions/{session['session_id']}/turns":
            return httpx.Response(202, json={"status": "accepted", "run_id": run_id})
        if request.url.path == f"/v1/runs/{run_id}/events":
            return httpx.Response(200, json={"events": events})
        if request.url.path == f"/v1/runs/{run_id}/approvals/{approval_id}":
            return httpx.Response(202, json=approval)
        if request.url.path.endswith("/cancel"):
            return httpx.Response(202, json=cancel)
        if request.url.path == f"/v1/runs/{run_id}/stream":
            return httpx.Response(200, content=stream_body)
        return httpx.Response(404, json={"error": {"message": "not found"}})

    return handler


def _normalize_contract(
    *,
    session_id: str,
    run_id: str,
    events: list[dict],
    approval_status: str,
    cancel_status: str,
    stream_events: list[dict],
) -> dict:
    return {
        "session_id_shape": session_id.startswith("ses-"),
        "run_id_shape": run_id.startswith("run-"),
        "event_types": [event["event_type"] for event in events],
        "approval_accepted": approval_status in {"queued", "running", "completed"},
        "cancel_accepted": cancel_status in {"cancelling", "cancelled", "completed"},
        "stream_event_ids": [event["id"] for event in stream_events],
        "stream_event_types": [event["event"] for event in stream_events],
    }


def _parse_sse(body: str) -> list[dict]:
    events = []
    normalized = body.replace("\r\n", "\n")
    for block in normalized.strip().split("\n\n"):
        record = {}
        for line in block.splitlines():
            if line.startswith("id:"):
                record["id"] = line[3:].strip()
            elif line.startswith("event:"):
                record["event"] = line[6:].strip()
            elif line.startswith("data:"):
                json.loads(line[5:].strip())
        if record:
            events.append(record)
    return events

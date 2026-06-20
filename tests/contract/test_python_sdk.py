import json

import httpx

from doge_sdk import DogeClient


def test_python_sdk_create_session_and_stream():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/sessions":
            return httpx.Response(200, json={"session_id": "ses-test", "title": "Test", "turns": []})
        if request.url.path == "/v1/sessions/ses-test/turns":
            return httpx.Response(202, json={"status": "accepted", "run_id": "run-test"})
        if request.url.path == "/v1/runs/run-test/stream":
            payload = json.dumps({"event_id": "evt-1", "run_id": "run-test"})
            return httpx.Response(200, content=f"id: 1\nevent: run_created\ndata: {payload}\n\n")
        return httpx.Response(404, json={"error": {"message": "not found"}})

    client = DogeClient(base_url="http://testserver", transport=httpx.MockTransport(handler))

    session = client.sessions.create("Test")
    run_id = session.create_turn("Analyze")
    events = list(client.runs.stream(run_id))

    assert session.session_id == "ses-test"
    assert run_id == "run-test"
    assert events[0].id == "1"


def test_python_sdk_reconnect_with_last_event_id():
    seen_header = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_header["last"] = request.headers.get("last-event-id")
        return httpx.Response(200, content='id: 2\nevent: tool_call\ndata: {"ok": true}\n\n')

    client = DogeClient(base_url="http://testserver", transport=httpx.MockTransport(handler))

    events = list(client.runs.stream("run-test", last_event_id="1"))

    assert seen_header["last"] == "1"
    assert events[0].type == "tool_call"


def test_python_sdk_approve_returns_accepted_queued_run():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/v1/runs/run-test/approvals/appr-1"
        return httpx.Response(202, json={"run_id": "run-test", "status": "queued"})

    client = DogeClient(base_url="http://testserver", transport=httpx.MockTransport(handler))

    run = client.runs.approve("run-test", "appr-1")

    assert run["status"] == "queued"

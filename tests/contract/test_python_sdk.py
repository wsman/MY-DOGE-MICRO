import json

import httpx
import pytest

from doge_sdk import AsyncDogeClient, DogeApiError, DogeClient


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


def test_python_sdk_session_run_sets_execution_profile():
    seen_body = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/sessions":
            return httpx.Response(200, json={"session_id": "ses-test", "title": "Test", "turns": []})
        if request.url.path == "/v1/sessions/ses-test/turns":
            seen_body.update(json.loads(request.content.decode("utf-8")))
            return httpx.Response(202, json={"status": "accepted", "run_id": "run-test"})
        return httpx.Response(404, json={"error": {"message": "not found"}})

    client = DogeClient(base_url="http://testserver", transport=httpx.MockTransport(handler))

    session = client.sessions.create("Test")
    run_id = session.run("Analyze", execution_profile="quant_code", document_ids=["doc-1"])

    assert run_id == "run-test"
    assert seen_body["model_policy"]["execution_profile"] == "quant_code"
    assert seen_body["document_ids"] == ["doc-1"]


def test_python_sdk_sends_bearer_and_request_id_and_redacts_error():
    seen_headers = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers["authorization"] = request.headers.get("authorization")
        seen_headers["request_id"] = request.headers.get("x-request-id")
        return httpx.Response(
            403,
            json={"error": {"message": "rejected Authorization: Bearer secret-token"}},
        )

    client = DogeClient(
        base_url="http://testserver",
        api_token="secret-token",
        request_id="req-123",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(DogeApiError) as excinfo:
        client.sessions.list()

    assert seen_headers == {
        "authorization": "Bearer secret-token",
        "request_id": "req-123",
    }
    assert "secret-token" not in str(excinfo.value)
    assert "Bearer [REDACTED]" in str(excinfo.value)


def test_python_sdk_redacts_key_value_secrets_from_api_errors():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            500,
            json={
                "detail": (
                    "provider failed MOONSHOT_API_KEY=moonshot-secret "
                    "client_secret=client-secret sk-live-secret"
                )
            },
        )

    client = DogeClient(base_url="http://testserver", transport=httpx.MockTransport(handler))

    with pytest.raises(DogeApiError) as excinfo:
        client.sessions.list()

    message = str(excinfo.value)
    assert "moonshot-secret" not in message
    assert "client-secret" not in message
    assert "sk-live-secret" not in message
    assert "MOONSHOT_API_KEY=[REDACTED]" in message
    assert "client_secret=[REDACTED]" in message
    assert "sk-[REDACTED]" in message


def test_python_sdk_reconnect_with_last_event_id():
    seen_header = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_header["last"] = request.headers.get("last-event-id")
        return httpx.Response(200, content='id: 2\nevent: tool_call\ndata: {"ok": true}\n\n')

    client = DogeClient(base_url="http://testserver", transport=httpx.MockTransport(handler))

    events = list(client.runs.stream("run-test", last_event_id="1"))

    assert seen_header["last"] == "1"
    assert events[0].type == "tool_call"


def test_python_sdk_stream_sends_auth_request_id_and_last_event_id():
    seen_headers = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers["authorization"] = request.headers.get("authorization")
        seen_headers["request_id"] = request.headers.get("x-request-id")
        seen_headers["last"] = request.headers.get("last-event-id")
        return httpx.Response(200, content='id: 2\nevent: tool_call\ndata: {"ok": true}\n\n')

    client = DogeClient(
        base_url="http://testserver",
        api_token="secret-token",
        request_id="req-123",
        transport=httpx.MockTransport(handler),
    )

    events = list(client.runs.stream("run-test", last_event_id="1"))

    assert seen_headers == {
        "authorization": "Bearer secret-token",
        "request_id": "req-123",
        "last": "1",
    }
    assert events[0].id == "2"


def test_python_sdk_stream_error_redacts_bearer_token_from_body():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            401,
            json={"error": {"message": "stream rejected Authorization: Bearer secret-token"}},
        )

    client = DogeClient(
        base_url="http://testserver",
        api_token="secret-token",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(DogeApiError) as excinfo:
        list(client.runs.stream("run-test"))

    assert "secret-token" not in str(excinfo.value)
    assert "Bearer [REDACTED]" in str(excinfo.value)


def test_python_sdk_auto_reconnects_stream_with_backoff():
    seen_headers = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.append(request.headers.get("last-event-id"))
        if len(seen_headers) == 1:
            raise httpx.ReadError("network dropped", request=request)
        return httpx.Response(200, content='id: 2\nevent: tool_call\ndata: {"ok": true}\n\n')

    client = DogeClient(base_url="http://testserver", transport=httpx.MockTransport(handler))

    events = list(client.runs.stream(
        "run-test",
        last_event_id="1",
        max_reconnects=1,
        backoff_seconds=0,
        sleep=lambda seconds: None,
    ))

    assert seen_headers == ["1", "1"]
    assert events[0].id == "2"


@pytest.mark.asyncio
async def test_async_python_sdk_create_session_and_stream():
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/sessions":
            return httpx.Response(200, json={"session_id": "ses-test", "title": "Test", "turns": []})
        if request.url.path == "/v1/sessions/ses-test/turns":
            return httpx.Response(202, json={"status": "accepted", "run_id": "run-test"})
        if request.url.path == "/v1/runs/run-test/stream":
            payload = json.dumps({"event_id": "evt-1", "run_id": "run-test"})
            return httpx.Response(200, content=f"id: 1\nevent: run_created\ndata: {payload}\n\n")
        return httpx.Response(404, json={"error": {"message": "not found"}})

    async with AsyncDogeClient(
        base_url="http://testserver",
        transport=httpx.MockTransport(handler),
    ) as client:
        session = await client.sessions.create("Test")
        run_id = await session.create_turn("Analyze")
        events = [event async for event in client.runs.stream(run_id)]

    assert session.session_id == "ses-test"
    assert run_id == "run-test"
    assert events[0].id == "1"


@pytest.mark.asyncio
async def test_async_python_sdk_sends_bearer_and_request_id_and_redacts_error():
    seen_headers = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen_headers["authorization"] = request.headers.get("authorization")
        seen_headers["request_id"] = request.headers.get("x-request-id")
        return httpx.Response(401, json={"detail": "token secret-token rejected"})

    async with AsyncDogeClient(
        base_url="http://testserver",
        api_token="secret-token",
        request_id="req-async",
        transport=httpx.MockTransport(handler),
    ) as client:
        with pytest.raises(DogeApiError) as excinfo:
            await client.sessions.list()

    assert seen_headers == {
        "authorization": "Bearer secret-token",
        "request_id": "req-async",
    }
    assert "secret-token" not in str(excinfo.value)
    assert "[REDACTED]" in str(excinfo.value)


@pytest.mark.asyncio
async def test_async_python_sdk_stream_error_redacts_bearer_token_from_body():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "stream token secret-token rejected"})

    async with AsyncDogeClient(
        base_url="http://testserver",
        api_token="secret-token",
        transport=httpx.MockTransport(handler),
    ) as client:
        with pytest.raises(DogeApiError) as excinfo:
            _events = [event async for event in client.runs.stream("run-test")]

    assert "secret-token" not in str(excinfo.value)
    assert "[REDACTED]" in str(excinfo.value)


def test_python_sdk_approve_returns_accepted_queued_run():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/v1/runs/run-test/approvals/appr-1"
        return httpx.Response(202, json={"run_id": "run-test", "status": "queued"})

    client = DogeClient(base_url="http://testserver", transport=httpx.MockTransport(handler))

    run = client.runs.approve("run-test", "appr-1")

    assert run["status"] == "queued"


def test_python_sdk_documents_get():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/v1/documents/doc-1"
        return httpx.Response(200, json={"document_id": "doc-1"})

    client = DogeClient(base_url="http://testserver", transport=httpx.MockTransport(handler))

    document = client.documents.get("doc-1")

    assert document["document_id"] == "doc-1"

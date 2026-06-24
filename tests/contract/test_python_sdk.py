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


def test_python_sdk_documents_upload_path_uses_multipart(tmp_path):
    source = tmp_path / "report.txt"
    source.write_text("alpha beta", encoding="utf-8")
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["content_type"] = request.headers.get("content-type")
        seen["body"] = request.content
        return httpx.Response(200, json={"document_id": "doc-upload", "filename": "report.txt"})

    client = DogeClient(base_url="http://testserver", transport=httpx.MockTransport(handler))

    document = client.documents.upload_path(source, content_type="text/plain")

    assert document["document_id"] == "doc-upload"
    assert seen["method"] == "POST"
    assert seen["path"] == "/v1/documents"
    assert seen["content_type"].startswith("multipart/form-data")
    assert b'report.txt' in seen["body"]
    assert b"alpha beta" in seen["body"]


def test_python_sdk_run_summary_platform_and_capability_resources():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/runs/run-1/summary":
            return httpx.Response(200, json={"summary": {"summary_id": "sum-1"}})
        if request.url.path == "/v1/runs/run-1/claims":
            return httpx.Response(200, json={"claims": [{"claim_id": "claim-1"}]})
        if request.url.path == "/v1/runs/run-1/citations":
            return httpx.Response(200, json={"citations": [{"citation_id": "cit-1"}]})
        if request.url.path == "/v1/runs/run-1/eval":
            return httpx.Response(200, json={"eval": {"coverage_ratio": 1.0}})
        if request.url.path == "/v1/workspaces" and request.method == "POST":
            seen["workspace_body"] = json.loads(request.content.decode("utf-8"))
            return httpx.Response(201, json={"workspace_id": "w-1"})
        if request.url.path == "/v1/home-queue":
            seen["home_query"] = dict(request.url.params)
            return httpx.Response(200, json={"pending_cases": [{"case_id": "case-1"}]})
        if request.url.path == "/v1/projects" and request.method == "GET":
            seen["project_query"] = dict(request.url.params)
            return httpx.Response(200, json={"projects": [{"project_id": "p-1"}]})
        if request.url.path == "/v1/research-cases/case-1/runs":
            body = json.loads(request.content.decode("utf-8"))
            if "template_id" in body:
                seen["template_run_body"] = body
                return httpx.Response(
                    201,
                    json={"case_id": "case-1", "run_id": "run-from-template", "template_id": "tpl-1"},
                )
            seen["case_run_body"] = body
            return httpx.Response(201, json={"case_id": "case-1", "run_id": "run-1"})
        if request.url.path == "/v1/research-cases/case-1/assets":
            if request.method == "POST":
                seen["asset_body"] = json.loads(request.content.decode("utf-8"))
                return httpx.Response(201, json={"asset_link_id": "asset-link-1"})
            return httpx.Response(200, json={"assets": [{"asset_link_id": "asset-link-1"}]})
        if request.url.path == "/v1/research-cases/case-1/decisions":
            if request.method == "POST":
                seen["decision_body"] = json.loads(request.content.decode("utf-8"))
                return httpx.Response(201, json={"decision_id": "decision-1"})
            return httpx.Response(200, json={"decisions": [{"decision_id": "decision-1"}]})
        if request.url.path == "/v1/research-cases/case-1/executions/preflight":
            seen["preflight_body"] = json.loads(request.content.decode("utf-8"))
            return httpx.Response(200, json={"valid": True})
        if request.url.path == "/v1/research-cases/case-1/executions":
            if request.method == "POST":
                seen["execution_body"] = json.loads(request.content.decode("utf-8"))
                return httpx.Response(202, json={"execution_id": "exec-1", "run_id": "run-2"})
            seen["execution_query"] = dict(request.url.params)
            return httpx.Response(200, json={"executions": [{"execution_id": "exec-1"}]})
        if request.url.path == "/v1/research-cases/case-1/review":
            return httpx.Response(200, json={"case": {"case_id": "case-1"}, "executions": []})
        if request.url.path == "/v1/workflow-templates" and request.method == "POST":
            seen["template_body"] = json.loads(request.content.decode("utf-8"))
            return httpx.Response(201, json={"template_id": "tpl-1"})
        if request.url.path == "/v1/capabilities":
            return httpx.Response(200, json={"capabilities": [{"capability_id": "maturity.production_ready"}]})
        return httpx.Response(404, json={"error": {"message": "not found"}})

    client = DogeClient(base_url="http://testserver", transport=httpx.MockTransport(handler))

    assert client.runs.summary("run-1")["summary_id"] == "sum-1"
    assert client.runs.claims("run-1")[0]["claim_id"] == "claim-1"
    assert client.runs.citations("run-1")[0]["citation_id"] == "cit-1"
    assert client.runs.evaluation("run-1")["coverage_ratio"] == 1.0
    assert client.platform.create_workspace("Desk")["workspace_id"] == "w-1"
    assert client.platform.home_queue(limit=7)["pending_cases"][0]["case_id"] == "case-1"
    assert client.platform.list_projects(workspace_id="w-1", limit=10)[0]["project_id"] == "p-1"
    assert client.platform.link_research_case_run("case-1", "run-1")["run_id"] == "run-1"
    assert client.platform.create_research_case_run_from_template(
        "case-1",
        "tpl-1",
        question="Analyze NVDA",
        model_policy={"max_tool_rounds": 3},
        inputs={"ticker": "NVDA"},
    )["run_id"] == "run-from-template"
    assert client.platform.add_case_asset("case-1", "document", "doc-1", asset_name="10-K")["asset_link_id"] == "asset-link-1"
    assert client.platform.list_case_assets("case-1")[0]["asset_link_id"] == "asset-link-1"
    assert client.platform.record_case_decision(
        "case-1",
        "approve",
        rationale="Supported",
        source_run_ids=["run-2"],
    )["decision_id"] == "decision-1"
    assert client.platform.list_case_decisions("case-1")[0]["decision_id"] == "decision-1"
    assert client.platform.preflight_case_execution("case-1", "tpl-1", inputs={"ticker": "NVDA"})["valid"] is True
    assert client.platform.execute_case_template("case-1", "tpl-1", inputs={"ticker": "NVDA"})["run_id"] == "run-2"
    assert client.platform.list_case_executions("case-1", limit=5)[0]["execution_id"] == "exec-1"
    assert client.platform.get_case_review("case-1")["case"]["case_id"] == "case-1"
    assert client.platform.create_workflow_template(
        "stock",
        "Stock",
        required_capabilities=["feature.workflow_templates"],
        eval_policy=["tool_success"],
        approval_policy={"publish": "required"},
        ui_schema={"layout": "stock"},
    )["template_id"] == "tpl-1"
    assert client.capabilities.list()[0]["capability_id"] == "maturity.production_ready"
    assert seen["workspace_body"] == {"name": "Desk", "description": ""}
    assert seen["home_query"] == {"limit": "7"}
    assert seen["project_query"] == {"limit": "10", "workspace_id": "w-1"}
    assert seen["case_run_body"] == {"run_id": "run-1", "link_type": "primary"}
    assert seen["template_run_body"]["template_id"] == "tpl-1"
    assert seen["template_run_body"]["model_policy"] == {"max_tool_rounds": 3}
    assert seen["template_run_body"]["inputs"] == {"ticker": "NVDA"}
    assert seen["asset_body"]["asset_type"] == "document"
    assert seen["asset_body"]["asset_name"] == "10-K"
    assert seen["decision_body"]["source_run_ids"] == ["run-2"]
    assert seen["preflight_body"]["template_id"] == "tpl-1"
    assert seen["preflight_body"]["inputs"] == {"ticker": "NVDA"}
    assert seen["execution_body"]["template_id"] == "tpl-1"
    assert seen["execution_query"] == {"limit": "5"}
    assert seen["template_body"]["input_schema"] == {}
    assert seen["template_body"]["required_capabilities"] == ["feature.workflow_templates"]
    assert seen["template_body"]["eval_policy"] == ["tool_success"]


@pytest.mark.asyncio
async def test_async_python_sdk_run_summary_platform_and_capability_resources():
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/runs/run-1/summary":
            return httpx.Response(200, json={"summary": {"summary_id": "sum-1"}})
        if request.url.path == "/v1/workspaces" and request.method == "GET":
            return httpx.Response(200, json={"workspaces": [{"workspace_id": "w-1"}]})
        if request.url.path == "/v1/research-cases/case-1/executions/preflight":
            return httpx.Response(200, json={"valid": True})
        if request.url.path == "/v1/research-cases/case-1/runs" and request.method == "POST":
            return httpx.Response(
                201,
                json={"case_id": "case-1", "run_id": "run-from-template", "template_id": "tpl-1"},
            )
        if request.url.path == "/v1/research-cases/case-1/executions" and request.method == "POST":
            return httpx.Response(202, json={"execution_id": "exec-1", "run_id": "run-from-execution"})
        if request.url.path == "/v1/research-cases/case-1/review":
            return httpx.Response(200, json={"case": {"case_id": "case-1"}})
        if request.url.path == "/v1/capabilities":
            return httpx.Response(200, json={"capabilities": [{"capability_id": "provider.kimi"}]})
        return httpx.Response(404, json={"error": {"message": "not found"}})

    async with AsyncDogeClient(
        base_url="http://testserver",
        transport=httpx.MockTransport(handler),
    ) as client:
        summary = await client.runs.summary("run-1")
        workspaces = await client.platform.list_workspaces()
        template_run = await client.platform.create_research_case_run_from_template(
            "case-1",
            "tpl-1",
            question="Analyze NVDA",
        )
        preflight = await client.platform.preflight_case_execution("case-1", "tpl-1")
        execution = await client.platform.execute_case_template("case-1", "tpl-1")
        review = await client.platform.get_case_review("case-1")
        capabilities = await client.capabilities.list()

    assert summary["summary_id"] == "sum-1"
    assert workspaces[0]["workspace_id"] == "w-1"
    assert template_run["run_id"] == "run-from-template"
    assert preflight["valid"] is True
    assert execution["run_id"] == "run-from-execution"
    assert review["case"]["case_id"] == "case-1"
    assert capabilities[0]["capability_id"] == "provider.kimi"

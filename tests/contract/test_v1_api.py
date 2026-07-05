import time

from fastapi.testclient import TestClient

from doge.config import reset_settings
from doge.interfaces.api import deps
from doge.interfaces.api.main import app


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


def _create_run(client: TestClient) -> str:
    session = client.post("/v1/sessions", json={"title": "API"}).json()
    return client.post(
        f"/v1/sessions/{session['session_id']}/turns",
        json={"message": "Analyze"},
    ).json()["run_id"]


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


def test_v1_post_turns_returns_202_with_run_id(tmp_path, monkeypatch):
    _reset_agent_deps(monkeypatch, tmp_path)
    with TestClient(app) as client:
        session = client.post("/v1/sessions", json={"title": "API"}).json()

        response = client.post(f"/v1/sessions/{session['session_id']}/turns", json={"message": "Analyze"})

    assert response.status_code == 202
    assert response.json()["run_id"].startswith("run-")


def test_v1_post_turns_persists_non_default_workflow(tmp_path, monkeypatch):
    # ADR-0028: a non-default workflow on the turn body must reach the persisted
    # run via the route-handler body->command seam (sessions.py create_turn).
    _reset_agent_deps(monkeypatch, tmp_path)
    with TestClient(app) as client:
        session = client.post("/v1/sessions", json={"title": "API"}).json()
        run_id = client.post(
            f"/v1/sessions/{session['session_id']}/turns",
            json={"message": "Analyze", "workflow": "portfolio_risk_review"},
        ).json()["run_id"]
        time.sleep(0.2)

        body = client.get(f"/v1/runs/{run_id}").json()

    assert body["workflow"] == "portfolio_risk_review"


def test_v1_post_turns_persists_default_workflow_when_absent(tmp_path, monkeypatch):
    # Absent workflow preserves the legacy default at the HTTP boundary.
    _reset_agent_deps(monkeypatch, tmp_path)
    with TestClient(app) as client:
        session = client.post("/v1/sessions", json={"title": "API"}).json()
        run_id = client.post(
            f"/v1/sessions/{session['session_id']}/turns",
            json={"message": "Analyze"},
        ).json()["run_id"]
        time.sleep(0.2)

        body = client.get(f"/v1/runs/{run_id}").json()

    assert body["workflow"] == "investment_research"


def test_v1_get_run_returns_status(tmp_path, monkeypatch):
    _reset_agent_deps(monkeypatch, tmp_path)
    with TestClient(app) as client:
        session = client.post("/v1/sessions", json={"title": "API"}).json()
        run_id = client.post(f"/v1/sessions/{session['session_id']}/turns", json={"message": "Analyze"}).json()["run_id"]
        time.sleep(0.2)

        response = client.get(f"/v1/runs/{run_id}")

    assert response.status_code == 200
    assert response.json()["status"] in {"queued", "running", "awaiting_approval", "completed"}


def test_v1_get_run_events_returns_sequence(tmp_path, monkeypatch):
    _reset_agent_deps(monkeypatch, tmp_path)
    with TestClient(app) as client:
        run_id = _create_run(client)

        response = client.get(f"/v1/runs/{run_id}/events")

    assert response.status_code == 200
    events = response.json()["events"]
    assert events[0]["sequence"] == 1
    assert events[0]["event_type"] == "run_created"


def test_v1_cancel_run_returns_accepted(tmp_path, monkeypatch):
    _reset_agent_deps(monkeypatch, tmp_path)
    with TestClient(app) as client:
        run_id = _create_run(client)

        response = client.post(f"/v1/runs/{run_id}/cancel")

    assert response.status_code == 202
    assert response.json()["run_id"] == run_id
    assert response.json()["status"] in {"cancelling", "cancelled", "completed"}


def test_v1_resolve_approval_returns_accepted(tmp_path, monkeypatch):
    _reset_agent_deps(monkeypatch, tmp_path)
    with TestClient(app) as client:
        run_id = _create_run(client)
        run = _wait_for_run(client, run_id, {"awaiting_approval"})
        approval_id = run["approvals"][0]["approval_id"]

        response = client.post(f"/v1/runs/{run_id}/approvals/{approval_id}", json={"approved": True})

    assert response.status_code == 202
    assert response.json()["run_id"] == run_id
    assert response.json()["status"] in {"queued", "running", "completed"}


def test_v1_explicit_resume_with_approval_returns_completed(tmp_path, monkeypatch):
    _reset_agent_deps(monkeypatch, tmp_path)
    with TestClient(app) as client:
        run_id = _create_run(client)
        run = _wait_for_run(client, run_id, {"awaiting_approval"})
        approval_id = run["approvals"][0]["approval_id"]

        response = client.post(
            f"/v1/runs/{run_id}/resume",
            json={"approval_id": approval_id, "approved": True},
        )

    assert response.status_code == 202
    body = response.json()
    assert body["run_id"] == run_id
    assert body["status"] == "completed"
    assert body["artifacts"]


def test_v1_explicit_resume_requires_approval_for_paused_run(tmp_path, monkeypatch):
    _reset_agent_deps(monkeypatch, tmp_path)
    with TestClient(app) as client:
        run_id = _create_run(client)
        _wait_for_run(client, run_id, {"awaiting_approval"})

        response = client.post(f"/v1/runs/{run_id}/resume", json={})

    assert response.status_code == 409
    assert "awaiting approval" in response.json()["error"]["message"]


def test_v1_explicit_resume_rejects_terminal_run(tmp_path, monkeypatch):
    _reset_agent_deps(monkeypatch, tmp_path)
    with TestClient(app) as client:
        run_id = _create_run(client)
        run = _wait_for_run(client, run_id, {"awaiting_approval"})
        approval_id = run["approvals"][0]["approval_id"]
        completed = client.post(
            f"/v1/runs/{run_id}/resume",
            json={"approval_id": approval_id, "approved": True},
        )
        assert completed.status_code == 202
        assert completed.json()["status"] == "completed"

        response = client.post(f"/v1/runs/{run_id}/resume", json={})

    assert response.status_code == 409
    assert "not resumable" in response.json()["error"]["message"]


def test_v1_stream_run_returns_sse_events(tmp_path, monkeypatch):
    _reset_agent_deps(monkeypatch, tmp_path)
    with TestClient(app) as client:
        run_id = _create_run(client)
        _wait_for_run(client, run_id, {"awaiting_approval", "completed"})

        with client.stream("GET", f"/v1/runs/{run_id}/stream") as response:
            body = response.read().decode("utf-8")

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert "event: run_created" in body
    assert "data:" in body


def test_optional_api_token_auth(tmp_path, monkeypatch):
    _reset_agent_deps(monkeypatch, tmp_path)
    monkeypatch.setenv("DOGE_API_TOKEN", "secret")

    with TestClient(app) as client:
        assert client.get("/v1/sessions").status_code == 401
        assert client.get("/v1/sessions", headers={"Authorization": "Bearer secret"}).status_code == 200
    monkeypatch.delenv("DOGE_API_TOKEN")


def test_health_ready_reports_daemon_subsystems(tmp_path, monkeypatch):
    _reset_agent_deps(monkeypatch, tmp_path)
    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["process_role"] == "all"
    assert set(body["checks"]) == {
        "database",
        "migration_version",
        "queue_depth",
        "worker_heartbeat",
        "outbox_backlog",
        "document_storage",
        "model_provider_configuration",
    }
    worker_heartbeat = body["checks"]["worker_heartbeat"]
    assert worker_heartbeat["loop_running"] is True
    assert set(worker_heartbeat["worker_metrics"]) == {
        "runs_processed",
        "runs_failed",
        "runs_cancelled",
        "avg_processing_latency_ms",
        "last_heartbeat_at",
        "active_run_count",
    }
    assert body["checks"]["model_provider_configuration"]["provider"] == "kimi"


def test_api_process_role_lifespan_does_not_start_worker(tmp_path, monkeypatch):
    _reset_agent_deps(monkeypatch, tmp_path)
    monkeypatch.setenv("DOGE_PROCESS_ROLE", "api")
    reset_settings()
    with TestClient(app) as client:
        response = client.get("/health/ready")

    try:
        assert response.status_code == 200
        body = response.json()
        assert body["process_role"] == "api"
        assert body["checks"]["worker_heartbeat"]["mode"] == "external"
        assert "worker_metrics" not in body["checks"]["worker_heartbeat"]
        assert deps._worker is None
    finally:
        monkeypatch.delenv("DOGE_PROCESS_ROLE", raising=False)
        reset_settings()


def test_v1_post_turns_reuses_idempotency_key(tmp_path, monkeypatch):
    _reset_agent_deps(monkeypatch, tmp_path)
    with TestClient(app) as client:
        session = client.post("/v1/sessions", json={"title": "API"}).json()
        headers = {"Idempotency-Key": "idem-1"}

        first = client.post(
            f"/v1/sessions/{session['session_id']}/turns",
            json={"message": "Analyze"},
            headers=headers,
        )
        second = client.post(
            f"/v1/sessions/{session['session_id']}/turns",
            json={"message": "Analyze"},
            headers=headers,
        )

    assert first.status_code == 202
    assert second.status_code == 202
    assert second.json()["run_id"] == first.json()["run_id"]


def test_v1_documents_accepts_multipart_upload(tmp_path, monkeypatch):
    _reset_agent_deps(monkeypatch, tmp_path)
    with TestClient(app) as client:
        response = client.post(
            "/v1/documents",
            files={"file": ("report.txt", b"alpha beta", "text/plain")},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["document_id"].startswith("doc-")
    assert body["filename"] == "report.txt"
    assert body["original_filename"] == "report.txt"
    assert body["file_hash"]
    assert body["mime_type"] == "text/plain"
    assert body["size_bytes"] == len(b"alpha beta")
    assert body["parsing_status"] == "parsed"
    assert body["content"] == "alpha beta"


def test_v1_documents_keeps_json_registration_compatibility(tmp_path, monkeypatch):
    _reset_agent_deps(monkeypatch, tmp_path)
    with TestClient(app) as client:
        created = client.post(
            "/v1/documents",
            json={"document_id": "doc-json", "filename": "memo.md", "content": "# memo"},
        )
        fetched = client.get("/v1/documents/doc-json")

    assert created.status_code == 200
    assert fetched.status_code == 200
    assert fetched.json()["document_id"] == "doc-json"
    assert fetched.json()["filename"] == "memo.md"
    assert fetched.json()["parsing_status"] == "parsed"


def test_v1_tools_returns_schemas(tmp_path, monkeypatch):
    _reset_agent_deps(monkeypatch, tmp_path)
    with TestClient(app) as client:
        response = client.get("/v1/tools")

    assert response.status_code == 200
    tools = response.json()["tools"]
    assert tools
    for schema in tools:
        assert schema["type"] == "function"
        function = schema["function"]
        assert function["name"]
        assert function["description"]
        assert schema["x-doge-category"]
        assert schema["x-doge-status"]
        metadata = schema["x-doge-metadata"]
        assert metadata["provider"]
        assert metadata["method_name"]


def test_v1_capabilities_full_app_smoke(tmp_path, monkeypatch):
    _reset_agent_deps(monkeypatch, tmp_path)
    monkeypatch.setenv("DOGE_FEATURE_CAPABILITY_REGISTRY", "1")
    monkeypatch.setenv("MOONSHOT_API_KEY", "moonshot-secret")
    reset_settings()

    with TestClient(app) as client:
        response = client.get("/v1/capabilities")

    assert response.status_code == 200
    body = response.json()
    assert body["snapshot_id"].startswith("cap-")
    assert body["redaction_version"] == "doge.capability_redaction.v1"
    assert "moonshot-secret" not in repr(body)
    assert body["capabilities"]


def test_v1_platform_full_app_feature_flag_smoke(tmp_path, monkeypatch):
    _reset_agent_deps(monkeypatch, tmp_path)
    monkeypatch.setenv("DOGE_FEATURE_PLATFORM_OBJECTS", "0")
    reset_settings()

    with TestClient(app) as client:
        response = client.get("/v1/workspaces")

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "platform objects API disabled"


def test_legacy_documents_route_uses_persisted_repository(tmp_path, monkeypatch):
    _reset_agent_deps(monkeypatch, tmp_path)
    with TestClient(app) as client:
        created = client.post(
            "/api/documents",
            json={"document_id": "doc-legacy", "filename": "legacy.md", "content": "# legacy"},
        )
        fetched = client.get("/v1/documents/doc-legacy")

    assert created.status_code == 200
    assert created.json()["document_id"] == "doc-legacy"
    assert fetched.status_code == 200
    assert fetched.json()["filename"] == "legacy.md"
    assert fetched.json()["parsing_status"] == "parsed"


def test_v1_portfolio_import_persists_csv_holdings(tmp_path, monkeypatch):
    _reset_agent_deps(monkeypatch, tmp_path)
    csv_payload = (
        "symbol,asset_class,sector,quantity,market_value,currency\n"
        "AAPL,equity,technology,10,2500,USD\n"
        "TLT,bond,rates,5,900,USD\n"
    )
    with TestClient(app) as client:
        response = client.post(
            "/v1/portfolios/import",
            data={"name": "Operator book", "portfolio_id": "portfolio-test"},
            files={"file": ("portfolio.csv", csv_payload.encode("utf-8"), "text/csv")},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["portfolio_id"] == "portfolio-test"
    assert body["name"] == "Operator book"
    assert body["total_market_value"] == 3400.0
    assert [holding["symbol"] for holding in body["holdings"]] == ["AAPL", "TLT"]


def test_v1_portfolio_import_rejects_invalid_csv(tmp_path, monkeypatch):
    _reset_agent_deps(monkeypatch, tmp_path)
    with TestClient(app) as client:
        response = client.post(
            "/v1/portfolios/import",
            files={"file": ("portfolio.csv", b"symbol,market_value\nAAPL,not-a-number\n", "text/csv")},
        )

    assert response.status_code == 400
    assert "market_value must be numeric" in response.json()["error"]["message"]

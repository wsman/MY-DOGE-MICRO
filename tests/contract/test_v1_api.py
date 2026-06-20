import time

from fastapi.testclient import TestClient

from doge.config import reset_settings
from doge.interfaces.api import deps
from doge.interfaces.api.main import app


def _reset_agent_deps(monkeypatch, tmp_path):
    monkeypatch.setenv("DOGE_AGENT_DB", str(tmp_path / "agent_state.db"))
    reset_settings()
    deps._persisted_research_agent_runtime = None
    deps._event_bus = None
    deps._worker = None
    deps._run_queue = None
    deps._idempotency_store = None


def test_v1_post_turns_returns_202_with_run_id(tmp_path, monkeypatch):
    _reset_agent_deps(monkeypatch, tmp_path)
    client = TestClient(app)
    session = client.post("/v1/sessions", json={"title": "API"}).json()

    response = client.post(f"/v1/sessions/{session['session_id']}/turns", json={"message": "Analyze"})

    assert response.status_code == 202
    assert response.json()["run_id"].startswith("run-")


def test_v1_get_run_returns_status(tmp_path, monkeypatch):
    _reset_agent_deps(monkeypatch, tmp_path)
    client = TestClient(app)
    session = client.post("/v1/sessions", json={"title": "API"}).json()
    run_id = client.post(f"/v1/sessions/{session['session_id']}/turns", json={"message": "Analyze"}).json()["run_id"]
    time.sleep(0.2)

    response = client.get(f"/v1/runs/{run_id}")

    assert response.status_code == 200
    assert response.json()["status"] in {"running", "awaiting_approval", "completed"}


def test_optional_api_token_auth(tmp_path, monkeypatch):
    _reset_agent_deps(monkeypatch, tmp_path)
    monkeypatch.setenv("DOGE_API_TOKEN", "secret")
    client = TestClient(app)

    assert client.get("/v1/sessions").status_code == 401
    assert client.get("/v1/sessions", headers={"Authorization": "Bearer secret"}).status_code == 200
    monkeypatch.delenv("DOGE_API_TOKEN")


def test_v1_post_turns_reuses_idempotency_key(tmp_path, monkeypatch):
    _reset_agent_deps(monkeypatch, tmp_path)
    client = TestClient(app)
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

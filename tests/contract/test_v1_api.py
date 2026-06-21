import time

from fastapi.testclient import TestClient

from doge.config import reset_settings
from doge.interfaces.api import deps
from doge.interfaces.api.main import app


def _reset_agent_deps(monkeypatch, tmp_path):
    monkeypatch.setenv("DOGE_AGENT_DB", str(tmp_path / "agent_state.db"))
    monkeypatch.setenv("DOGE_DOCUMENT_STORAGE_DIR", str(tmp_path / "documents"))
    reset_settings()
    deps._persisted_research_agent_runtime = None
    deps._event_bus = None
    deps._worker = None
    deps._run_queue = None
    deps._idempotency_store = None
    deps._agent_unit_of_work = None
    deps._file_upload_service = None


def test_v1_post_turns_returns_202_with_run_id(tmp_path, monkeypatch):
    _reset_agent_deps(monkeypatch, tmp_path)
    with TestClient(app) as client:
        session = client.post("/v1/sessions", json={"title": "API"}).json()

        response = client.post(f"/v1/sessions/{session['session_id']}/turns", json={"message": "Analyze"})

    assert response.status_code == 202
    assert response.json()["run_id"].startswith("run-")


def test_v1_get_run_returns_status(tmp_path, monkeypatch):
    _reset_agent_deps(monkeypatch, tmp_path)
    with TestClient(app) as client:
        session = client.post("/v1/sessions", json={"title": "API"}).json()
        run_id = client.post(f"/v1/sessions/{session['session_id']}/turns", json={"message": "Analyze"}).json()["run_id"]
        time.sleep(0.2)

        response = client.get(f"/v1/runs/{run_id}")

    assert response.status_code == 200
    assert response.json()["status"] in {"queued", "running", "awaiting_approval", "completed"}


def test_optional_api_token_auth(tmp_path, monkeypatch):
    _reset_agent_deps(monkeypatch, tmp_path)
    monkeypatch.setenv("DOGE_API_TOKEN", "secret")

    with TestClient(app) as client:
        assert client.get("/v1/sessions").status_code == 401
        assert client.get("/v1/sessions", headers={"Authorization": "Bearer secret"}).status_code == 200
    monkeypatch.delenv("DOGE_API_TOKEN")


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

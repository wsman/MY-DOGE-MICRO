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


def test_v1_large_multipart_upload_keeps_document_shape(tmp_path, monkeypatch):
    _reset_agent_deps(monkeypatch, tmp_path)
    payload = b"alpha beta gamma" * 1024
    with TestClient(app) as client:
        created = client.post(
            "/v1/documents",
            files={"file": ("large.txt", payload, "text/plain")},
        )
        fetched = client.get(f"/v1/documents/{created.json()['document_id']}")

    assert created.status_code == 200
    assert fetched.status_code == 200
    body = fetched.json()
    assert body["filename"] == "large.txt"
    assert body["size_bytes"] == len(payload)
    assert body["file_hash"]
    assert body["storage_path"]
    assert body["parsing_status"] in {"parsed", "uploaded"}


def test_v1_oversize_multipart_upload_returns_413(tmp_path, monkeypatch):
    monkeypatch.setenv("DOGE_DOCUMENT_MAX_BYTES", "4")
    _reset_agent_deps(monkeypatch, tmp_path)
    with TestClient(app) as client:
        response = client.post(
            "/v1/documents",
            files={"file": ("large.txt", b"12345", "text/plain")},
        )

    assert response.status_code == 413

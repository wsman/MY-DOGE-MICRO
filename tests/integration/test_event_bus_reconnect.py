import time

from fastapi.testclient import TestClient

from doge.config import reset_settings
from doge.interfaces.api import deps
from doge.interfaces.api.main import app


def test_v1_stream_supports_last_event_id_reconnect(tmp_path, monkeypatch):
    monkeypatch.setenv("DOGE_AGENT_DB", str(tmp_path / "agent_state.db"))
    reset_settings()
    deps._persisted_research_agent_runtime = None
    deps._event_bus = None
    deps._event_subscriber = None
    deps._worker = None
    deps._run_queue = None
    deps._idempotency_store = None
    deps._agent_unit_of_work = None
    with TestClient(app) as client:
        session = client.post("/v1/sessions", json={"title": "Stream"}).json()
        run_id = client.post(f"/v1/sessions/{session['session_id']}/turns", json={"message": "Analyze"}).json()["run_id"]
        time.sleep(0.3)
        events = client.get(f"/v1/runs/{run_id}/events").json()["events"]
        assert len(events) > 2

        with client.stream("GET", f"/v1/runs/{run_id}/stream", headers={"Last-Event-ID": "1"}) as response:
            text = response.read().decode("utf-8")

    assert "id: 2" in text

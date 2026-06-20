from fastapi.testclient import TestClient

from doge.application.composition import build_research_agent_runtime
from doge.interfaces.api import deps
from doge.interfaces.api.main import app


def _client_with_runtime(runtime):
    app.dependency_overrides[deps.get_research_agent_runtime] = lambda: runtime
    return TestClient(app)


def test_agent_run_lifecycle_and_approval():
    runtime = build_research_agent_runtime()
    client = _client_with_runtime(runtime)
    try:
        created = client.post("/api/agent/runs", json={
            "workflow": "investment_research",
            "question": "Analyze earnings quality and portfolio risk.",
            "portfolio_id": "portfolio-demo",
            "model_policy": {"max_tool_rounds": 8},
        })
        assert created.status_code == 200
        body = created.json()
        assert body["status"] == "awaiting_approval"
        run_id = body["run_id"]
        approval_id = body["approvals"][0]["approval_id"]

        events = client.get(f"/api/agent/runs/{run_id}/events")
        assert events.status_code == 200
        assert len(events.json()["events"]) >= 4

        approved = client.post(
            f"/api/agent/runs/{run_id}/approvals/{approval_id}",
            json={"approved": True},
        )
        assert approved.status_code == 200
        assert approved.json()["status"] == "completed"

        artifacts = client.get(f"/api/agent/runs/{run_id}/artifacts")
        assert artifacts.json()["artifacts"][0]["kind"] == "investment_memo"
    finally:
        app.dependency_overrides.clear()


def test_agent_run_404():
    runtime = build_research_agent_runtime()
    client = _client_with_runtime(runtime)
    try:
        assert client.get("/api/agent/runs/missing").status_code == 404
    finally:
        app.dependency_overrides.clear()

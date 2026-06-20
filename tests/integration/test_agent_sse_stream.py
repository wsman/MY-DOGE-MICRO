import json

from fastapi.testclient import TestClient

from doge.application.agent.research_runtime import ResearchAgentRuntime, ScriptedAgentModel
from doge.interfaces.api import deps
from doge.interfaces.api.main import app


def test_agent_sse_stream_returns_existing_events():
    runtime = ResearchAgentRuntime(model=ScriptedAgentModel())
    app.dependency_overrides[deps.get_research_agent_runtime] = lambda: runtime
    try:
        client = TestClient(app)
        created = client.post("/api/agent/runs", json={
            "question": "Analyze the company.",
            "model_policy": {"max_tool_rounds": 8},
        })
        run_id = created.json()["run_id"]
        with client.stream("GET", f"/api/agent/runs/{run_id}/stream") as resp:
            assert resp.status_code == 200
            events = []
            for line in resp.iter_lines():
                if isinstance(line, bytes):
                    line = line.decode("utf-8")
                if line.startswith("data: "):
                    events.append(json.loads(line.removeprefix("data: ")))
    finally:
        app.dependency_overrides.clear()

    assert events
    assert events[0]["event_type"] == "run_created"

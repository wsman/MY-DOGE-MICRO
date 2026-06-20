import json

from fastapi.testclient import TestClient

from doge.application.contracts.response import MacroReportResponse
from doge.interfaces.api import deps
from doge.interfaces.api.main import app


class FakeMacroUseCase:
    def execute(self, request):
        return MacroReportResponse(content=f"macro body for {request.market}")


def test_macro_run_sse_success_integration():
    app.dependency_overrides[deps.get_generate_macro_report_use_case] = lambda: FakeMacroUseCase()
    try:
        client = TestClient(app)
        with client.stream("POST", "/api/macro/run", json={"market": "cn"}) as resp:
            assert resp.status_code == 200
            events = []
            for line in resp.iter_lines():
                if isinstance(line, bytes):
                    line = line.decode("utf-8")
                if line.startswith("data: "):
                    events.append(json.loads(line.removeprefix("data: ")))
    finally:
        app.dependency_overrides.clear()

    assert [event["progress"] for event in events] == [10, 40, 80, 100]

import json

from fastapi.testclient import TestClient

from doge.application.contracts.response import MacroReportResponse
from doge.interfaces.api import deps
from doge.interfaces.api.main import app


class FakeMacroUseCase:
    def __init__(self, response=None, exc=None):
        self.response = response or MacroReportResponse(content="macro body")
        self.exc = exc
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        if self.exc:
            raise self.exc
        return self.response


def _events(resp):
    payloads = []
    for line in resp.iter_lines():
        if isinstance(line, bytes):
            line = line.decode("utf-8")
        if line.startswith("data: "):
            payloads.append(json.loads(line.removeprefix("data: ")))
    return payloads


def test_macro_run_sse_uses_injected_use_case_success():
    fake = FakeMacroUseCase()
    app.dependency_overrides[deps.get_generate_macro_report_use_case] = lambda: fake
    try:
        client = TestClient(app)
        with client.stream("POST", "/api/macro/run", json={"market": "us"}) as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]
            events = _events(resp)
    finally:
        app.dependency_overrides.clear()

    assert [event["progress"] for event in events] == [10, 40, 80, 100]
    assert fake.requests[0].market == "us"


def test_macro_run_sse_reports_fixed_error_message():
    fake = FakeMacroUseCase(exc=RuntimeError("secret key sk-test"))
    app.dependency_overrides[deps.get_generate_macro_report_use_case] = lambda: fake
    try:
        client = TestClient(app)
        with client.stream("POST", "/api/macro/run", json={}) as resp:
            events = _events(resp)
    finally:
        app.dependency_overrides.clear()

    assert events[-1] == {"progress": -1, "message": "macro run failed"}
    assert "sk-test" not in json.dumps(events)

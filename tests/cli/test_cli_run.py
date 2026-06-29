import json
from types import SimpleNamespace

from doge.core.domain.agent_models import AgentEvent, EventType
from doge.interfaces.cli.commands import run as run_command


def test_cli_run_uses_runtime_container(monkeypatch, capsys):
    captured = {}

    class FakeExecuteRun:
        async def execute(self, question, **kwargs):
            captured["question"] = question
            captured["kwargs"] = kwargs
            return SimpleNamespace(
                run_id="run-cli",
                status=SimpleNamespace(value="completed"),
                artifacts=[],
                approvals=[],
                events=[],
            )

    class FakeRuntimeContainer:
        def build_execute_run_use_case(self):
            return FakeExecuteRun()

    monkeypatch.setattr(run_command, "_runtime_container", lambda: FakeRuntimeContainer())

    run_command.cmd_run(
        SimpleNamespace(
            question="Analyze AAPL",
            session="ses-cli",
            market="us",
            language="en",
            portfolio=None,
            max_tool_rounds=3,
            json=False,
            trace=False,
            follow=False,
            jsonl=False,
        )
    )

    out = capsys.readouterr().out
    assert "run_id=run-cli" in out
    assert "status=completed" in out
    assert captured == {
        "question": "Analyze AAPL",
        "kwargs": {
            "session_id": "ses-cli",
            "market": "us",
            "language": "en",
            "portfolio_id": None,
            "model_policy": {"max_tool_rounds": 3},
        },
    }


def test_cli_run_jsonl_emits_redacted_event_lines(monkeypatch, capsys):
    class FakeExecuteRun:
        async def execute(self, question, **kwargs):
            return SimpleNamespace(
                run_id="run-cli",
                status=SimpleNamespace(value="completed"),
                artifacts=[],
                approvals=[],
                events=[
                    AgentEvent(
                        event_id="evt-1",
                        run_id="run-cli",
                        event_type=EventType.ERROR,
                        payload={"api_key": "sk-run-secret", "message": "Authorization: Bearer run-secret"},
                    )
                ],
            )

    class FakeRuntimeContainer:
        def build_execute_run_use_case(self):
            return FakeExecuteRun()

    monkeypatch.setattr(run_command, "_runtime_container", lambda: FakeRuntimeContainer())

    run_command.cmd_run(
        SimpleNamespace(
            question="Analyze AAPL",
            session="ses-cli",
            market="us",
            language="en",
            portfolio="portfolio-demo",
            max_tool_rounds=3,
            json=False,
            trace=False,
            follow=True,
            jsonl=True,
        )
    )

    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert lines[0] == {
        "artifact": None,
        "run_id": "run-cli",
        "status": "completed",
        "type": "run_summary",
    }
    assert lines[1]["type"] == "event"
    assert lines[1]["event"]["payload"]["api_key"] == "<redacted>"
    assert "run-secret" not in json.dumps(lines, ensure_ascii=False)

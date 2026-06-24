from types import SimpleNamespace

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
            portfolio="portfolio-demo",
            max_tool_rounds=3,
            json=False,
            trace=False,
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
            "portfolio_id": "portfolio-demo",
            "model_policy": {"max_tool_rounds": 3},
        },
    }

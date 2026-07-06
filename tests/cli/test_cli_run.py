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
    assert "Next actions:" in out
    assert "Open artifacts" in out
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
    assert "Next actions:" not in capsys.readouterr().out


def test_cli_run_resume_uses_explicit_resume_use_case(monkeypatch, capsys):
    captured = {}

    class FakeResumeRun:
        async def execute(self, run_id, *, approval_id=None, approved=True):
            captured["run_id"] = run_id
            captured["approval_id"] = approval_id
            captured["approved"] = approved
            return SimpleNamespace(
                run_id=run_id,
                status=SimpleNamespace(value="completed"),
                artifacts=[SimpleNamespace(title="Memo")],
                approvals=[],
                events=[],
            )

    class FakeRuntimeContainer:
        def build_resume_run_use_case(self):
            return FakeResumeRun()

    monkeypatch.setattr(run_command, "_runtime_container", lambda: FakeRuntimeContainer())

    run_command.cmd_run(
        SimpleNamespace(
            question=None,
            resume="run-cli",
            approval="appr-1",
            deny=False,
            session=None,
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
    assert "artifact=Memo" in out
    assert "Next actions:" in out
    assert captured == {"run_id": "run-cli", "approval_id": "appr-1", "approved": True}


def test_cli_run_awaiting_approval_prints_next_action(monkeypatch, capsys):
    class FakeExecuteRun:
        async def execute(self, question, **kwargs):
            return SimpleNamespace(
                run_id="run-cli",
                status=SimpleNamespace(value="awaiting_approval"),
                artifacts=[],
                approvals=[SimpleNamespace(approval_id="appr-1", status="pending")],
                events=[],
            )

    class FakeRuntimeContainer:
        def build_execute_run_use_case(self):
            return FakeExecuteRun()

    monkeypatch.setattr(run_command, "_runtime_container", lambda: FakeRuntimeContainer())

    run_command.cmd_run(
        SimpleNamespace(
            question="Analyze AAPL",
            session=None,
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
    assert "pending_approvals=appr-1" in out
    assert "Approve or deny" in out


def test_cli_run_deny_requires_approval(monkeypatch, capsys):
    class FailingRuntimeContainer:
        def __getattr__(self, _name):
            raise AssertionError("runtime container must not be used")

    monkeypatch.setattr(run_command, "_runtime_container", lambda: FailingRuntimeContainer())

    try:
        run_command.cmd_run(
            SimpleNamespace(
                question=None,
                resume="run-cli",
                approval=None,
                deny=True,
                session=None,
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
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("cmd_run should exit when --deny has no --approval")

    assert "--deny requires --approval" in capsys.readouterr().err


def test_cli_run_approval_flags_require_resume(monkeypatch, capsys):
    class FailingRuntimeContainer:
        def __getattr__(self, _name):
            raise AssertionError("runtime container must not be used")

    monkeypatch.setattr(run_command, "_runtime_container", lambda: FailingRuntimeContainer())

    try:
        run_command.cmd_run(
            SimpleNamespace(
                question="Analyze AAPL",
                resume=None,
                approval="appr-1",
                deny=False,
                session=None,
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
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("cmd_run should exit when approval flags are used without --resume")

    assert "--approval/--deny require --resume" in capsys.readouterr().err

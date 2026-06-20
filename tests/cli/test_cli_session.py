import subprocess
import sys
import os
from types import SimpleNamespace

from doge.config import reset_settings
from doge.interfaces.cli.main import main
from doge.interfaces.cli.commands import session as session_command


def test_cli_session_creates_new_session(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DOGE_AGENT_DB", str(tmp_path / "agent_state.db"))
    reset_settings()

    main(["session", "--title", "CLI Demo"])

    out = capsys.readouterr().out
    assert "session_id=ses-" in out
    assert "title=CLI Demo" in out


def test_cli_session_resume_lists_turns(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DOGE_AGENT_DB", str(tmp_path / "agent_state.db"))
    reset_settings()
    main(["session", "--title", "Resume Demo"])
    session_id = capsys.readouterr().out.splitlines()[0].split("=", 1)[1]

    main(["session", "--resume", session_id])

    out = capsys.readouterr().out
    assert f"session_id={session_id}" in out
    assert "turns=0" in out


def test_cli_session_persists_across_processes(tmp_path):
    db = tmp_path / "agent_state.db"
    env = os.environ.copy()
    env.update({"DOGE_AGENT_DB": str(db), "PYTHONPATH": "src"})
    create = subprocess.run(
        [sys.executable, "-m", "doge.interfaces.cli.main", "session", "--title", "Persisted"],
        text=True,
        capture_output=True,
        env=env,
        check=True,
    )
    session_id = create.stdout.splitlines()[0].split("=", 1)[1]

    resume = subprocess.run(
        [sys.executable, "-m", "doge.interfaces.cli.main", "session", "--resume", session_id],
        text=True,
        capture_output=True,
        env=env,
        check=True,
    )

    assert f"session_id={session_id}" in resume.stdout


def test_cli_approval_does_not_synchronously_complete(monkeypatch, capsys):
    class FakeExecuteRun:
        async def execute(self, *args, **kwargs):
            return SimpleNamespace(
                run_id="run-cli",
                status=SimpleNamespace(value="awaiting_approval"),
            )

    lines = iter(["Analyze AAPL", "/approve appr-1", "/exit"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(lines))
    monkeypatch.setattr(session_command.composition, "build_execute_run_use_case", lambda: FakeExecuteRun())
    monkeypatch.setattr(
        session_command.composition,
        "build_persisted_research_agent_runtime",
        lambda: (_ for _ in ()).throw(AssertionError("runtime continuation must not run")),
    )

    session_command._interactive_loop("ses-cli", "us")

    out = capsys.readouterr().out
    assert "run_id=run-cli status=awaiting_approval" in out
    assert "approval continuation is unsupported in the CLI" in out

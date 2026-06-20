import subprocess
import sys
import os

from doge.config import reset_settings
from doge.interfaces.cli.main import main


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

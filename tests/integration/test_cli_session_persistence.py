import subprocess
import sys
import os


def test_cli_session_resume_with_message_persists_turn(tmp_path):
    db = tmp_path / "agent_state.db"
    env = os.environ.copy()
    env.update({"DOGE_AGENT_DB": str(db), "PYTHONPATH": "src"})
    create = subprocess.run(
        [sys.executable, "-m", "doge.interfaces.cli.main", "session", "--title", "Process Demo"],
        text=True,
        capture_output=True,
        env=env,
        check=True,
    )
    session_id = create.stdout.splitlines()[0].split("=", 1)[1]

    subprocess.run(
        [
            sys.executable,
            "-m",
            "doge.interfaces.cli.main",
            "session",
            "--resume",
            session_id,
            "--message",
            "Analyze earnings quality",
        ],
        text=True,
        capture_output=True,
        env=env,
        check=True,
    )
    resume = subprocess.run(
        [sys.executable, "-m", "doge.interfaces.cli.main", "session", "--resume", session_id],
        text=True,
        capture_output=True,
        env=env,
        check=True,
    )

    assert "Analyze earnings quality" in resume.stdout

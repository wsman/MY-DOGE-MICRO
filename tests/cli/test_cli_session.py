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


def test_cli_embedded_approval_continues_run(monkeypatch, capsys):
    class FakeExecuteRun:
        async def execute(self, *args, **kwargs):
            return SimpleNamespace(
                run_id="run-cli",
                status=SimpleNamespace(value="awaiting_approval"),
                approvals=[
                    SimpleNamespace(
                        approval_id="appr-1",
                        action="publish",
                        risk_level="high",
                        status="pending",
                    )
                ],
            )

    class FakeRuntime:
        async def resolve_approval(self, run_id, approval_id, approved):
            assert (run_id, approval_id, approved) == ("run-cli", "appr-1", True)
            return SimpleNamespace(run_id=run_id, status=SimpleNamespace(value="queued"), artifacts=[], approvals=[])

        async def run_to_pause_or_completion(self, run_id):
            return SimpleNamespace(
                run_id=run_id,
                status=SimpleNamespace(value="completed"),
                artifacts=[SimpleNamespace(title="Memo")],
                approvals=[],
                session_id="ses-cli",
            )

    lines = iter(["Analyze AAPL", "/approve appr-1", "/exit"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(lines))
    monkeypatch.setattr(session_command.composition, "build_execute_run_use_case", lambda: FakeExecuteRun())
    monkeypatch.setattr(
        session_command.composition,
        "build_persisted_research_agent_runtime",
        lambda: FakeRuntime(),
    )

    session_command._interactive_loop("ses-cli", "us")

    out = capsys.readouterr().out
    assert "run_id=run-cli status=awaiting_approval" in out
    assert "approval_required run_id=run-cli approval_id=appr-1" in out
    assert "run_id=run-cli status=completed" in out
    assert "artifact=Memo" in out


def test_cli_gateway_approval_prints_resolution_path(monkeypatch, capsys):
    run = SimpleNamespace(
        run_id="run-cli",
        approvals=[
            SimpleNamespace(
                approval_id="appr-1",
                action="publish",
                risk_level="high",
                status="pending",
            )
        ],
    )

    session_command._print_pending_approvals(run, session_id="ses-cli", mode="gateway")

    out = capsys.readouterr().out
    assert "resolve_via=POST /v1/runs/run-cli/approvals/appr-1" in out
    assert "resume_via=doge session --mode gateway --resume ses-cli --approve run-cli:appr-1" in out


def test_cli_gateway_interactive_posts_turn_to_daemon(monkeypatch, capsys):
    captured = []

    def fake_daemon_request(args, method, path, body=None):
        captured.append((method, path, body))
        return {"run_id": "run-gateway"}

    lines = iter(["Analyze AAPL", "/exit"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(lines))
    monkeypatch.setattr(session_command, "_daemon_request", fake_daemon_request)
    monkeypatch.setattr(
        session_command.composition,
        "build_execute_run_use_case",
        lambda: (_ for _ in ()).throw(AssertionError("gateway mode must not use embedded runtime")),
    )

    session_command._interactive_loop("ses-cli", "us", mode="gateway")

    out = capsys.readouterr().out
    assert "run_id=run-gateway status=accepted" in out
    assert captured[0][0] == "POST"
    assert captured[0][1] == "/v1/sessions/ses-cli/turns"
    assert captured[0][2]["model_policy"]["execution_profile"] == "financial_research"


def test_cli_attach_registers_real_file_and_passes_document_id(tmp_path, monkeypatch, capsys):
    db = tmp_path / "agent_state.db"
    document_dir = tmp_path / "documents"
    source = tmp_path / "report.txt"
    source.write_text("alpha beta", encoding="utf-8")
    monkeypatch.setenv("DOGE_AGENT_DB", str(db))
    monkeypatch.setenv("DOGE_DOCUMENT_STORAGE_DIR", str(document_dir))
    reset_settings()
    captured = {}

    class FakeExecuteRun:
        async def execute(self, *args, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                run_id="run-cli",
                status=SimpleNamespace(value="completed"),
            )

    lines = iter([f"/attach {source}", "Analyze attached file", "/exit"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(lines))
    monkeypatch.setattr(session_command.composition, "build_execute_run_use_case", lambda: FakeExecuteRun())

    session_command._interactive_loop("ses-cli", "us")

    out = capsys.readouterr().out
    assert "attached=doc-" in out
    assert "status=parsed" in out
    assert captured["document_ids"][0].startswith("doc-")
    assert document_dir.exists()

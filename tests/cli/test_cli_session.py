import json
import subprocess
import sys
import os
from types import SimpleNamespace

from doge.config import reset_settings
from doge.core.domain.agent_models import AgentArtifact, AgentEvent, EventType
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
        async def resolve_approval(self, scope, run_id, approval_id, approved):
            assert scope.tenant_id == "local"
            assert (run_id, approval_id, approved) == ("run-cli", "appr-1", True)
            return SimpleNamespace(run_id=run_id, status=SimpleNamespace(value="queued"), artifacts=[], approvals=[])

        async def run_to_pause_or_completion(self, scope, run_id):
            assert scope.tenant_id == "local"
            return SimpleNamespace(
                run_id=run_id,
                status=SimpleNamespace(value="completed"),
                artifacts=[SimpleNamespace(title="Memo")],
                approvals=[],
                session_id="ses-cli",
            )

    lines = iter(["Analyze AAPL", "/approve appr-1", "/exit"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(lines))

    class FakeRuntimeContainer:
        def build_execute_run_use_case(self):
            return FakeExecuteRun()

        def build_persisted_research_agent_runtime(self):
            return FakeRuntime()

    monkeypatch.setattr(session_command, "_runtime_container", lambda: FakeRuntimeContainer())

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

    class FakeSessions:
        def create_turn(self, session_id, message, **kwargs):
            captured.append((session_id, message, kwargs))
            return "run-gateway"

    class FakeRuns:
        def stream(self, run_id):
            captured.append(("stream", run_id))
            return [{"event_type": "run_queued", "run_id": run_id}]

        def get(self, run_id):
            captured.append(("get", run_id))
            return {
                "events": [{"event_type": "tool_call", "payload": {"ticker": "AAPL"}}],
                "artifacts": [{"artifact_id": "art-1", "title": "Gateway Memo"}],
            }

    class FakeGatewayClient:
        def __init__(self):
            self.sessions = FakeSessions()
            self.runs = FakeRuns()

        def close(self):
            captured.append(("closed",))

    lines = iter(["Analyze AAPL", "/trace", "/artifacts", "/exit"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(lines))
    monkeypatch.setattr(session_command, "_gateway_client", lambda args: FakeGatewayClient())

    class FailingRuntimeContainer:
        def __getattr__(self, _name):
            raise AssertionError("gateway mode must not use embedded runtime")

    monkeypatch.setattr(session_command, "_runtime_container", lambda: FailingRuntimeContainer())

    session_command._interactive_loop("ses-cli", "us", mode="gateway")

    out = capsys.readouterr().out
    assert "run_id=run-gateway status=accepted" in out
    assert "stream_via=GET" not in out
    assert '"event_type": "run_queued"' in out
    assert '"event_type": "tool_call"' in out
    assert '"title": "Gateway Memo"' in out
    assert captured[0][0] == "ses-cli"
    assert captured[0][1] == "Analyze AAPL"
    assert captured[0][2]["model_policy"]["execution_profile"] == "financial_research"
    assert ("stream", "run-gateway") in captured
    assert captured.count(("get", "run-gateway")) == 2


def test_cli_gateway_session_commands_use_sdk_client(monkeypatch, capsys):
    calls = []

    class FakeSession:
        data = {"session_id": "ses-gateway", "title": "SDK Gateway", "turns": [], "updated_at": "now"}

    class FakeSessions:
        def create(self, title):
            calls.append(("create", title))
            return FakeSession()

        def list(self, limit):
            calls.append(("list", limit))
            return [FakeSession.data]

    class FakeRuns:
        def approve(self, run_id, approval_id, approved):
            calls.append(("approve", run_id, approval_id, approved))
            return {"status": "queued"}

    class FakeGatewayClient:
        def __init__(self):
            self.sessions = FakeSessions()
            self.runs = FakeRuns()

        def close(self):
            calls.append(("closed",))

    monkeypatch.setattr(session_command, "_gateway_client", lambda args: FakeGatewayClient())

    args = SimpleNamespace(
        list=False,
        resume=None,
        title="SDK Gateway",
        limit=20,
        daemon_url="http://127.0.0.1:8901",
        api_token="test-token",
    )
    session_command._cmd_gateway_session(args)
    session_command._cmd_gateway_session(SimpleNamespace(**{**args.__dict__, "list": True}))
    session_command._resolve_gateway_approval(args, "run-1", "appr-1", True)

    out = capsys.readouterr().out
    assert "session_id=ses-gateway" in out
    assert "gateway_approval_resolved run_id=run-1 approval_id=appr-1 approved=true" in out
    assert ("create", "SDK Gateway") in calls
    assert ("list", 20) in calls
    assert ("approve", "run-1", "appr-1", True) in calls
    assert calls.count(("closed",)) == 3


def test_cli_gateway_session_message_jsonl_streams_sdk_events(monkeypatch, capsys):
    calls = []

    class FakeSession:
        data = {"session_id": "ses-gateway", "title": "SDK Gateway", "turns": []}

    class FakeSessions:
        def get(self, session_id):
            calls.append(("get_session", session_id))
            return FakeSession()

        def create_turn(self, session_id, message, **kwargs):
            calls.append(("create_turn", session_id, message, kwargs))
            return "run-gateway"

    class FakeRuns:
        def stream(self, run_id):
            calls.append(("stream", run_id))
            return [{"event_type": "run_queued", "payload": {"api_key": "sk-gateway-secret"}}]

    class FakeGatewayClient:
        def __init__(self):
            self.sessions = FakeSessions()
            self.runs = FakeRuns()

        def close(self):
            calls.append(("closed",))

    monkeypatch.setattr(session_command, "_gateway_client", lambda args: FakeGatewayClient())

    args = SimpleNamespace(
        list=False,
        resume="ses-gateway",
        message="Analyze AAPL",
        market="us",
        approve=None,
        deny=None,
        follow=True,
        jsonl=True,
        interactive=False,
        daemon_url="http://127.0.0.1:8901",
        api_token="test-token",
    )

    session_command._cmd_gateway_session(args)

    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert lines[0] == {"run_id": "run-gateway", "status": "accepted", "type": "run_accepted"}
    assert lines[1]["type"] == "event"
    assert lines[1]["event"]["payload"]["api_key"] == "<redacted>"
    assert "sk-gateway-secret" not in json.dumps(lines, ensure_ascii=False)
    assert ("get_session", "ses-gateway") in calls
    create_turn = next(call for call in calls if call[0] == "create_turn")
    assert create_turn[1] == "ses-gateway"
    assert create_turn[2] == "Analyze AAPL"
    assert create_turn[3]["market"] == "us"
    assert create_turn[3]["model_policy"]["execution_profile"] == "financial_research"
    assert ("stream", "run-gateway") in calls


def test_cli_gateway_attach_uses_sdk_document_upload(tmp_path, monkeypatch, capsys):
    source = tmp_path / "report.txt"
    source.write_text("alpha beta", encoding="utf-8")
    captured = []

    class FakeDocuments:
        def upload_path(self, path):
            captured.append(("upload_path", path))
            return {"document_id": "doc-gateway", "filename": "report.txt", "parsing_status": "parsed"}

    class FakeSessions:
        def create_turn(self, session_id, message, **kwargs):
            captured.append((session_id, message, kwargs))
            return "run-gateway"

    class FakeRuns:
        def stream(self, run_id):
            captured.append(("stream", run_id))
            return [{"event_type": "run_queued", "run_id": run_id}]

    class FakeGatewayClient:
        def __init__(self):
            self.documents = FakeDocuments()
            self.sessions = FakeSessions()
            self.runs = FakeRuns()

        def close(self):
            captured.append(("closed",))

    lines = iter([f"/attach {source}", "Analyze attached", "/exit"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(lines))
    monkeypatch.setattr(session_command, "_gateway_client", lambda args: FakeGatewayClient())

    class FailingGatewayContainer:
        def build_file_upload_service(self):
            raise AssertionError("gateway attach must use SDK")

    monkeypatch.setattr(session_command, "_gateway_container", lambda: FailingGatewayContainer())

    session_command._interactive_loop("ses-cli", "us", mode="gateway")

    out = capsys.readouterr().out
    assert "attached=doc-gateway" in out
    assert captured[0] == ("upload_path", str(source))
    assert captured[2][2]["document_ids"] == ["doc-gateway"]
    assert ("stream", "run-gateway") in captured


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

    class FakeRuntimeContainer:
        def build_execute_run_use_case(self):
            return FakeExecuteRun()

    monkeypatch.setattr(session_command, "_runtime_container", lambda: FakeRuntimeContainer())

    session_command._interactive_loop("ses-cli", "us")

    out = capsys.readouterr().out
    assert "attached=doc-" in out
    assert "status=parsed" in out
    assert captured["document_ids"][0].startswith("doc-")
    assert document_dir.exists()


def test_cli_trace_and_artifact_output_redacts_sensitive_payloads(monkeypatch, capsys):
    run = SimpleNamespace(
        events=[
            AgentEvent(
                event_id="evt-1",
                run_id="run-cli",
                event_type=EventType.ERROR,
                payload={
                    "message": "Authorization: Bearer trace-secret MOONSHOT_API_KEY=moonshot-secret",
                    "api_key": "sk-trace-secret",
                },
            )
        ],
        artifacts=[
            AgentArtifact(
                artifact_id="art-1",
                kind="trace",
                title="Debug",
                content="client_secret=client-secret",
                run_id="run-cli",
                data={"access_token": "access-secret"},
            )
        ],
    )

    class FakeResumeRun:
        def execute(self, run_id):
            assert run_id == "run-cli"
            return run

    class FakeRuntimeContainer:
        def build_resume_run_use_case(self):
            return FakeResumeRun()

    monkeypatch.setattr(session_command, "_runtime_container", lambda: FakeRuntimeContainer())

    session_command._print_last_run("run-cli", field="events")
    session_command._print_last_run("run-cli", field="artifacts")

    out = capsys.readouterr().out
    assert "trace-secret" not in out
    assert "moonshot-secret" not in out
    assert "sk-trace-secret" not in out
    assert "client-secret" not in out
    assert "access-secret" not in out
    assert "Bearer [REDACTED]" in out
    assert "MOONSHOT_API_KEY=<redacted>" in out
    assert "\"api_key\": \"<redacted>\"" in out
    assert "\"access_token\": \"<redacted>\"" in out

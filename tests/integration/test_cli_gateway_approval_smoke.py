from __future__ import annotations

import socket
import threading
import time
import urllib.request

import pytest
import uvicorn

from doge.config import reset_settings
from doge.interfaces.api import deps
from doge.interfaces.api.main import app
from doge.interfaces.cli.main import main
from doge_sdk import DogeClient


@pytest.fixture
def gateway_url(tmp_path, monkeypatch):
    _reset_agent_deps(monkeypatch, tmp_path)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    host, port = sock.getsockname()
    sock.close()
    server = uvicorn.Server(
        uvicorn.Config(app, host=host, port=port, log_level="warning"),
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    base_url = f"http://{host}:{port}"
    deadline = time.time() + 5
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url}/health/ready", timeout=0.5) as response:
                if response.status == 200:
                    break
        except Exception:
            time.sleep(0.1)
    else:
        server.should_exit = True
        thread.join(timeout=5)
        pytest.fail("gateway smoke server did not start")

    try:
        yield base_url
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        _reset_agent_deps(monkeypatch, tmp_path)


def test_cli_gateway_approval_resume_smoke_over_real_v1_http(gateway_url, capsys):
    main(["session", "--mode", "gateway", "--title", "Gateway Smoke", "--daemon-url", gateway_url])
    session_id = _value_from_output(capsys.readouterr().out, "session_id")

    main([
        "session",
        "--mode",
        "gateway",
        "--resume",
        session_id,
        "--message",
        "Analyze AAPL gateway approval smoke",
        "--follow",
        "--daemon-url",
        gateway_url,
    ])
    submit_out = capsys.readouterr().out
    run_id = _accepted_run_id(submit_out)
    assert '"event_type": "approval_requested"' in submit_out

    sdk = DogeClient(base_url=gateway_url)
    try:
        run = _wait_for_status(sdk, run_id, {"awaiting_approval"})
        approval_id = run["approvals"][0]["approval_id"]

        main([
            "session",
            "--mode",
            "gateway",
            "--resume",
            session_id,
            "--approve",
            f"{run_id}:{approval_id}",
            "--follow",
            "--daemon-url",
            gateway_url,
        ])
        approve_out = capsys.readouterr().out
        assert f"gateway_approval_resolved run_id={run_id} approval_id={approval_id} approved=true" in approve_out
        assert '"event_type": "artifact_created"' in approve_out
        completed = _wait_for_status(sdk, run_id, {"completed"})
        events = sdk.runs.events(run_id)
        assert completed["artifacts"]
        assert any(event["event_type"] == "approval_resolved" for event in events)
        assert any(event["event_type"] == "artifact_created" for event in events)

        deny_run_id = sdk.sessions.get(session_id).create_turn(
            "Analyze AAPL gateway denial smoke",
            model_policy={"execution_profile": "financial_research"},
        )
        deny_run = _wait_for_status(sdk, deny_run_id, {"awaiting_approval"})
        deny_approval_id = deny_run["approvals"][0]["approval_id"]

        main([
            "session",
            "--mode",
            "gateway",
            "--resume",
            session_id,
            "--deny",
            f"{deny_run_id}:{deny_approval_id}",
            "--follow",
            "--daemon-url",
            gateway_url,
        ])
        deny_out = capsys.readouterr().out
        assert f"gateway_approval_resolved run_id={deny_run_id} approval_id={deny_approval_id} approved=false" in deny_out
        assert "status=failed" in deny_out
        _wait_for_status(sdk, deny_run_id, {"failed"})
        deny_events = sdk.runs.events(deny_run_id)
        assert any(event["event_type"] == "approval_resolved" for event in deny_events)
    finally:
        sdk.close()


def _reset_agent_deps(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("DOGE_PROCESS_ROLE", raising=False)
    monkeypatch.setenv("DOGE_AGENT_DB", str(tmp_path / "agent_state.db"))
    monkeypatch.setenv("DOGE_DOCUMENT_STORAGE_DIR", str(tmp_path / "documents"))
    reset_settings()
    deps._research_agent_runtime = None
    deps._persisted_research_agent_runtime = None
    deps._event_bus = None
    deps._event_subscriber = None
    deps._worker = None
    deps._run_queue = None
    deps._idempotency_store = None
    deps._agent_unit_of_work = None
    deps._runtime_outbox_publisher = None
    deps._file_upload_service = None
    deps._enterprise_governance_repository = None
    deps._run_scope_resolver = None


def _value_from_output(output: str, key: str) -> str:
    prefix = f"{key}="
    for line in output.splitlines():
        if line.startswith(prefix):
            return line.split("=", 1)[1]
    raise AssertionError(f"{key} not found in output:\n{output}")


def _accepted_run_id(output: str) -> str:
    for line in output.splitlines():
        if line.startswith("run_id="):
            return line.split()[0].split("=", 1)[1]
    raise AssertionError(f"run_id not found in output:\n{output}")


def _wait_for_status(client: DogeClient, run_id: str, statuses: set[str], timeout: float = 5.0) -> dict:
    deadline = time.time() + timeout
    body: dict = {}
    while time.time() < deadline:
        body = client.runs.get(run_id)
        if body["status"] in statuses:
            return body
        time.sleep(0.1)
    assert body.get("status") in statuses
    return body

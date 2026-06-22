import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = ROOT / "scripts" / "daemon_soak.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("daemon_soak", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_daemon_soak_runner_writes_evidence(tmp_path):
    module = _load_module()

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/health/ready":
            return httpx.Response(200, json={"status": "ready"})
        if path == "/v1/sessions" and request.method == "POST":
            return httpx.Response(200, json={"session_id": "session-soak"})
        if path == "/v1/documents" and request.method == "POST":
            return httpx.Response(200, json={"document_id": "doc-soak"})
        if path == "/v1/sessions/session-soak/turns" and request.method == "POST":
            return httpx.Response(202, json={"run_id": "run-soak"})
        if path == "/v1/runs/run-soak" and request.method == "GET":
            return httpx.Response(200, json={"run_id": "run-soak", "status": "completed", "approvals": []})
        if path == "/v1/runs/run-soak/events":
            return httpx.Response(200, json={"events": [{"sequence": 1, "event_type": "run_completed"}]})
        if path == "/v1/tools":
            return httpx.Response(200, json={"tools": [{"name": "lookup_evidence"}]})
        return httpx.Response(404, json={"error": {"message": path}})

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://testserver")
    output = module.run_soak(
        module.SoakConfig(
            base_url="http://testserver",
            duration_seconds=0,
            interval_seconds=0,
            output_dir=tmp_path,
        ),
        client=client,
        sleep=lambda _: None,
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema"] == "doge.daemon_soak.v1"
    assert payload["summary"] == {"passed": True, "iterations": 1, "failures": 0}
    assert payload["iterations"][0]["run_id"] == "run-soak"
    assert len(payload["checkpoints"]) == 2
    assert payload["checkpoints"][0]["label"] == "start"
    assert payload["checkpoints"][-1]["label"] == "final"


def test_daemon_soak_runner_records_optional_checkpoint_metadata(tmp_path):
    module = _load_module()
    agent_db = tmp_path / "agent_state.db"
    agent_db.write_bytes(b"sqlite")
    log_path = tmp_path / "uvicorn.err.log"
    log_path.write_text("INFO: ready\n", encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/health/ready":
            return httpx.Response(200, json={"status": "ready"})
        if path == "/v1/sessions" and request.method == "POST":
            return httpx.Response(200, json={"session_id": "session-soak"})
        if path == "/v1/documents" and request.method == "POST":
            return httpx.Response(200, json={"document_id": "doc-soak"})
        if path == "/v1/sessions/session-soak/turns" and request.method == "POST":
            return httpx.Response(202, json={"run_id": "run-soak"})
        if path == "/v1/runs/run-soak" and request.method == "GET":
            return httpx.Response(200, json={"run_id": "run-soak", "status": "completed", "approvals": []})
        if path == "/v1/runs/run-soak/events":
            return httpx.Response(200, json={"events": [{"sequence": 1, "event_type": "run_completed"}]})
        if path == "/v1/tools":
            return httpx.Response(200, json={"tools": [{"name": "lookup_evidence"}]})
        return httpx.Response(404, json={"error": {"message": path}})

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://testserver")
    output = module.run_soak(
        module.SoakConfig(
            base_url="http://testserver",
            duration_seconds=0,
            interval_seconds=0,
            output_dir=tmp_path,
            daemon_pid=os.getpid(),
            agent_db_path=agent_db,
            log_path=log_path,
        ),
        client=client,
        sleep=lambda _: None,
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    checkpoint = payload["checkpoints"][0]
    assert checkpoint["health_ready"] is True
    assert checkpoint["agent_db"]["size_bytes"] == len(b"sqlite")
    assert checkpoint["log"]["traceback_lines"] == 0
    assert checkpoint["daemon_process"]["pid"] == os.getpid()


def test_daemon_soak_help_lists_checkpoint_options():
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--help"],
        capture_output=True,
        check=True,
        text=True,
    )
    help_text = result.stdout
    assert "--checkpoint-seconds" in help_text
    assert "--daemon-pid" in help_text
    assert "--agent-db-path" in help_text
    assert "--log-path" in help_text

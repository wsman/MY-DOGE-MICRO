from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _request(method: str, url: str, *, token: str | None = None) -> tuple[int, dict[str, Any] | str]:
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers, method=method)
    try:
        with urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8")
            try:
                payload: dict[str, Any] | str = json.loads(body) if body else {}
            except json.JSONDecodeError:
                payload = body
            return response.status, payload
    except HTTPError as exc:
        body = exc.read().decode("utf-8")
        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            payload = body
        return exc.code, payload


def _base_env(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": f"{ROOT / 'src'};{env.get('PYTHONPATH', '')}",
            "DOGE_DB_DIR": str(tmp_path / "data"),
            "DOGE_AGENT_DB": str(tmp_path / "data" / "agent_state.db"),
            "DOGE_DOCUMENT_STORAGE_DIR": str(tmp_path / "documents"),
            "OPENBLAS_NUM_THREADS": "1",
            "OMP_NUM_THREADS": "1",
        }
    )
    return env


def _start_doged(port: int, env: dict[str, str]) -> subprocess.Popen[str]:
    return subprocess.Popen(
        [sys.executable, "-m", "doge.interfaces.daemon.main", "serve", "--port", str(port)],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _wait_ready(base_url: str, token: str, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            status, payload = _request("GET", f"{base_url}/api/health", token=token)
            if status == 200 and isinstance(payload, dict) and payload.get("status") == "ok":
                return
        except (URLError, ConnectionError, OSError) as exc:
            last_error = exc
        time.sleep(0.1)
    raise RuntimeError(f"Timed out waiting for doged health: {last_error}")


def _run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = output_dir / "doged-remote-bind-gate-smoke-2026-06-22.json"
    token = "remote-bind-smoke-token"
    denied_port = _free_port()
    allowed_port = _free_port()
    checks: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix="doge-remote-bind-smoke-") as tmp:
        tmp_path = Path(tmp)

        denied_env = _base_env(tmp_path / "denied")
        denied_env.update({"DOGE_BIND_HOST": "0.0.0.0"})
        denied_process = _start_doged(denied_port, denied_env)
        try:
            try:
                denied_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                denied_process.kill()
                denied_process.wait(timeout=5)
            denied_stdout, denied_stderr = denied_process.communicate()
        finally:
            if denied_process.poll() is None:
                denied_process.terminate()
        checks.append(
            {
                "name": "unapproved_remote_bind_rejected",
                "returncode": denied_process.returncode,
                "stderr_contains_gate": "ADR-0007 loopback guarantee" in denied_stderr
                or "ADR-0007 remote-bind promotion" in denied_stderr,
                "stdout_tail": denied_stdout[-500:],
                "stderr_tail": denied_stderr[-1500:],
            }
        )

        allowed_env = _base_env(tmp_path / "allowed")
        allowed_env.update(
            {
                "DOGE_BIND_HOST": "0.0.0.0",
                "DOGE_ALLOW_REMOTE_BIND": "1",
                "DOGE_AUTH_MODE": "enterprise",
                "DOGE_AUTH_STATIC_BEARER_TOKEN": token,
                "DOGE_AUTH_STATIC_SUBJECT": "operator@example.test",
                "DOGE_AUTH_STATIC_TENANT_ID": "tenant-remote-bind",
                "DOGE_AUTH_STATIC_ROLES": "tenant_admin",
                "DOGE_CORS_ALLOW_ORIGINS": "https://research.example.internal",
                "DOGE_API_TLS_TERMINATION_REQUIRED": "1",
            }
        )
        allowed_process = _start_doged(allowed_port, allowed_env)
        allowed_stdout = ""
        allowed_stderr = ""
        forced_shutdown = False
        try:
            _wait_ready(f"http://127.0.0.1:{allowed_port}", token, args.timeout_seconds)
            missing = _request("GET", f"http://127.0.0.1:{allowed_port}/v1/sessions")
            health = _request("GET", f"http://127.0.0.1:{allowed_port}/api/health", token=token)
            checks.append(
                {
                    "name": "approved_remote_bind_started_with_enterprise_auth",
                    "process_running": allowed_process.poll() is None,
                    "missing_bearer_status": missing[0],
                    "authorized_health_status": health[0],
                    "authorized_health_payload": health[1],
                }
            )
        finally:
            allowed_process.terminate()
            try:
                allowed_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                allowed_process.kill()
                forced_shutdown = True
                allowed_process.wait(timeout=5)
            allowed_stdout, allowed_stderr = allowed_process.communicate()

    expected = {
        "unapproved_remote_bind_rejected": lambda item: item["returncode"] != 0 and item["stderr_contains_gate"],
        "approved_remote_bind_started_with_enterprise_auth": lambda item: item["process_running"]
        and item["missing_bearer_status"] == 401
        and item["authorized_health_status"] == 200
        and isinstance(item["authorized_health_payload"], dict)
        and item["authorized_health_payload"].get("status") == "ok",
    }
    for check in checks:
        check["passed"] = expected[check["name"]](check)

    evidence = {
        "schema": "doge.doged_remote_bind_gate_smoke.v1",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "result": "passed" if all(item["passed"] for item in checks) else "failed",
        "bind_host": "0.0.0.0",
        "provider": "local_enterprise_static_bearer_fixture",
        "checks": checks,
        "approved_process": {
            "returncode": allowed_process.returncode,
            "shutdown_requested_by_smoke": True,
            "forced_shutdown": forced_shutdown,
            "stdout_tail": allowed_stdout[-1000:],
            "stderr_tail": allowed_stderr[-2000:],
        },
    }
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    if evidence["result"] != "passed":
        raise SystemExit(f"doged remote-bind gate smoke failed; see {evidence_path}")
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local doged remote-bind promotion gate smoke.")
    parser.add_argument("--output-dir", default="production/qa/evidence/manual", help="Directory for JSON evidence.")
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    args = parser.parse_args()
    evidence = _run(args)
    print(json.dumps({"result": evidence["result"], "checks": evidence["checks"]}, indent=2))


if __name__ == "__main__":
    main()

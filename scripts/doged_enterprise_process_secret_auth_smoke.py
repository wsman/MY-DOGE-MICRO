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


def _request(
    method: str,
    url: str,
    *,
    token: str | None = None,
    json_body: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> tuple[int, dict[str, Any] | str, dict[str, str]]:
    data = None
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if request_id:
        headers["X-Request-ID"] = request_id
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8")
            try:
                payload: dict[str, Any] | str = json.loads(body) if body else {}
            except json.JSONDecodeError:
                payload = body
            return response.status, payload, dict(response.headers)
    except HTTPError as exc:
        body = exc.read().decode("utf-8")
        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            payload = body
        return exc.code, payload, dict(exc.headers)


def _wait_ready(base_url: str, token: str, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            status, _, _ = _request("GET", f"{base_url}/api/health", token=token)
            if status == 200:
                return
        except (URLError, ConnectionError, OSError) as exc:
            last_error = exc
        time.sleep(0.1)
    raise RuntimeError(f"Timed out waiting for doged health: {last_error}")


def _run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = output_dir / "doged-enterprise-process-secret-auth-smoke-2026-06-22.json"
    token = "doged-process-secret-smoke-token"
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"

    with tempfile.TemporaryDirectory(prefix="doge-enterprise-process-secret-smoke-") as tmp:
        tmp_path = Path(tmp)
        helper = tmp_path / "secret_provider_fixture.py"
        helper.write_text(
            "\n".join(
                [
                    "import sys",
                    "name = sys.argv[1] if len(sys.argv) > 1 else ''",
                    "if name == 'auth.static_bearer_token':",
                    f"    print({token!r})",
                    "    raise SystemExit(0)",
                    "raise SystemExit(2)",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        command = [sys.executable, str(helper), "{name}"]
        env = os.environ.copy()
        for name in [
            "DOGE_AUTH_STATIC_BEARER_TOKEN",
            "DOGE_AUTH_OIDC_ISSUER",
            "DOGE_AUTH_OIDC_AUDIENCE",
            "DOGE_AUTH_OIDC_JWKS_URL",
        ]:
            env.pop(name, None)
        env.update(
            {
                "PYTHONPATH": f"{ROOT / 'src'};{env.get('PYTHONPATH', '')}",
                "DOGE_AUTH_MODE": "enterprise",
                "DOGE_AUTH_STATIC_SUBJECT": "operator@example.test",
                "DOGE_AUTH_STATIC_TENANT_ID": "tenant-secret",
                "DOGE_AUTH_STATIC_ROLES": "tenant_admin,portfolio_manager",
                "DOGE_SECRET_PROVIDER": "process",
                "DOGE_SECRET_PROCESS_COMMAND_JSON": json.dumps(command),
                "DOGE_SECRET_ALLOWED_NAMES": "auth.static_bearer_token",
                "DOGE_DB_DIR": str(tmp_path / "data"),
                "DOGE_AGENT_DB": str(tmp_path / "data" / "agent_state.db"),
                "DOGE_DOCUMENT_STORAGE_DIR": str(tmp_path / "documents"),
                "DOGE_BIND_HOST": "127.0.0.1",
                "OPENBLAS_NUM_THREADS": "1",
                "OMP_NUM_THREADS": "1",
            }
        )
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "doge.interfaces.api.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--log-level",
                "warning",
            ],
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        checks: list[dict[str, Any]] = []
        forced_shutdown = False
        try:
            _wait_ready(base_url, token, args.timeout_seconds)

            missing = _request("GET", f"{base_url}/v1/sessions")
            checks.append({"name": "missing_bearer_rejected", "status_code": missing[0]})

            wrong = _request("GET", f"{base_url}/v1/sessions", token="wrong-token")
            checks.append({"name": "wrong_bearer_rejected", "status_code": wrong[0]})

            session = _request(
                "POST",
                f"{base_url}/v1/sessions",
                token=token,
                request_id="req-doged-secret-session",
                json_body={"title": "Enterprise process secret smoke"},
            )
            session_payload = session[1] if isinstance(session[1], dict) else {}
            checks.append(
                {
                    "name": "authorized_session_create",
                    "status_code": session[0],
                    "tenant_id": session_payload.get("tenant_id"),
                    "session_id_present": bool(session_payload.get("session_id")),
                }
            )

            created = _request(
                "POST",
                f"{base_url}/v1/documents",
                token=token,
                request_id="req-doged-secret-doc-create",
                json_body={"document_id": "doc-secret", "filename": "memo.txt", "content": "secret alpha"},
            )
            created_payload = created[1] if isinstance(created[1], dict) else {}
            checks.append(
                {
                    "name": "authorized_document_create_grants_acl",
                    "status_code": created[0],
                    "tenant_id": created_payload.get("tenant_id"),
                    "document_id": created_payload.get("document_id"),
                }
            )

            audit = _request("GET", f"{base_url}/v1/audit/events", token=token)
            audit_payload = audit[1] if isinstance(audit[1], dict) else {}
            audit_events = audit_payload.get("events", [])
            checks.append(
                {
                    "name": "authorized_audit_list_tenant_scoped",
                    "status_code": audit[0],
                    "tenant_ids": sorted({item.get("tenant_id") for item in audit_events}),
                    "event_types": [item.get("event_type") for item in audit_events],
                }
            )
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                forced_shutdown = True
                process.wait(timeout=5)
            stdout, stderr = process.communicate()

    expected = {
        "missing_bearer_rejected": lambda item: item["status_code"] == 401,
        "wrong_bearer_rejected": lambda item: item["status_code"] == 401,
        "authorized_session_create": lambda item: item["status_code"] == 200
        and item["tenant_id"] == "tenant-secret"
        and item["session_id_present"],
        "authorized_document_create_grants_acl": lambda item: item["status_code"] == 200
        and item["tenant_id"] == "tenant-secret"
        and item["document_id"] == "doc-secret",
        "authorized_audit_list_tenant_scoped": lambda item: item["status_code"] == 200
        and item["tenant_ids"] == ["tenant-secret"]
        and "document_create" in item["event_types"],
    }
    for check in checks:
        check["passed"] = expected[check["name"]](check)
    evidence = {
        "schema": "doge.doged_enterprise_process_secret_auth_smoke.v1",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "result": "passed" if all(item["passed"] for item in checks) else "failed",
        "base_url": base_url,
        "auth_mode": "enterprise",
        "provider": "process_secret_fixture",
        "secret_provider": "process",
        "secret_names": ["auth.static_bearer_token"],
        "checks": checks,
        "process": {
            "returncode": process.returncode,
            "shutdown_requested_by_smoke": True,
            "forced_shutdown": forced_shutdown,
            "stdout_tail": stdout[-1000:],
            "stderr_tail": stderr[-2000:],
        },
    }
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    if evidence["result"] != "passed":
        raise SystemExit(f"doged enterprise process-secret auth smoke failed; see {evidence_path}")
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local doged enterprise process-secret auth smoke.")
    parser.add_argument("--output-dir", default="production/qa/evidence/manual", help="Directory for JSON evidence.")
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    args = parser.parse_args()
    evidence = _run(args)
    print(json.dumps({"result": evidence["result"], "checks": evidence["checks"]}, indent=2))


if __name__ == "__main__":
    main()

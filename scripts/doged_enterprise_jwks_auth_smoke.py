from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm


ROOT = Path(__file__).resolve().parents[1]
KEY_ID = "doge-local-jwks-smoke-key"
ISSUER = "http://127.0.0.1/local-idp"
AUDIENCE = "doge-api"


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


class _JwksFixture:
    def __init__(self, jwks: dict[str, Any]) -> None:
        self.jwks = jwks
        self.requests: list[str] = []

    def start(self) -> tuple[HTTPServer, threading.Thread, str]:
        fixture = self
        port = _free_port()

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802 - stdlib callback name
                fixture.requests.append(self.path)
                if self.path not in {"/.well-known/jwks.json", "/jwks.json"}:
                    self.send_response(404)
                    self.end_headers()
                    return
                payload = json.dumps(fixture.jwks).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, format: str, *args: Any) -> None:
                return

        server = HTTPServer(("127.0.0.1", port), Handler)
        thread = threading.Thread(target=server.serve_forever, name="doge-jwks-smoke", daemon=True)
        thread.start()
        return server, thread, f"http://127.0.0.1:{port}/.well-known/jwks.json"


def _run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = output_dir / "doged-enterprise-jwks-auth-smoke-2026-06-22.json"
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = json.loads(RSAAlgorithm.to_jwk(private_key.public_key()))
    public_jwk.update({"kid": KEY_ID, "alg": "RS256", "use": "sig"})
    jwks_fixture = _JwksFixture({"keys": [public_jwk]})
    jwks_server, jwks_thread, jwks_url = jwks_fixture.start()
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    valid_token = _token(private_key, {"jti": "jwks-smoke-valid"})
    wrong_audience_token = _token(
        private_key,
        {"aud": "wrong-audience", "tenant_id": "tenant-jwks"},
    )
    wrong_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    invalid_signature_token = _token(wrong_key, {"jti": "jwks-smoke-wrong-key"})

    process: subprocess.Popen[str] | None = None
    stdout = ""
    stderr = ""
    forced_shutdown = False
    checks: list[dict[str, Any]] = []
    try:
        with tempfile.TemporaryDirectory(prefix="doge-enterprise-jwks-smoke-") as tmp:
            tmp_path = Path(tmp)
            env = os.environ.copy()
            env.update(
                {
                    "PYTHONPATH": f"{ROOT / 'src'};{env.get('PYTHONPATH', '')}",
                    "DOGE_AUTH_MODE": "enterprise",
                    "DOGE_AUTH_OIDC_ISSUER": ISSUER,
                    "DOGE_AUTH_OIDC_AUDIENCE": AUDIENCE,
                    "DOGE_AUTH_OIDC_JWKS_URL": jwks_url,
                    "DOGE_AUTH_OIDC_ALGORITHMS": "RS256",
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
            try:
                _wait_ready(base_url, valid_token, args.timeout_seconds)

                missing = _request("GET", f"{base_url}/v1/sessions")
                checks.append({"name": "missing_bearer_rejected", "status_code": missing[0]})

                wrong_audience = _request("GET", f"{base_url}/v1/sessions", token=wrong_audience_token)
                checks.append({"name": "wrong_audience_rejected", "status_code": wrong_audience[0]})

                invalid_signature = _request("GET", f"{base_url}/v1/sessions", token=invalid_signature_token)
                checks.append({"name": "invalid_signature_rejected", "status_code": invalid_signature[0]})

                session = _request(
                    "POST",
                    f"{base_url}/v1/sessions",
                    token=valid_token,
                    request_id="req-doged-jwks-session",
                    json_body={"title": "Enterprise JWKS auth smoke"},
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
                    token=valid_token,
                    request_id="req-doged-jwks-doc-create",
                    json_body={"document_id": "doc-jwks", "filename": "memo.txt", "content": "jwks alpha"},
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

                listed = _request(
                    "GET",
                    f"{base_url}/v1/documents",
                    token=valid_token,
                    request_id="req-doged-jwks-doc-list",
                )
                listed_payload = listed[1] if isinstance(listed[1], dict) else {}
                checks.append(
                    {
                        "name": "authorized_document_list_sees_created_doc",
                        "status_code": listed[0],
                        "document_ids": [item.get("document_id") for item in listed_payload.get("documents", [])],
                    }
                )

                audit = _request("GET", f"{base_url}/v1/audit/events", token=valid_token)
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

                checks.append(
                    {
                        "name": "jwks_endpoint_was_used",
                        "request_count": len(jwks_fixture.requests),
                        "paths": sorted(set(jwks_fixture.requests)),
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
    finally:
        jwks_server.shutdown()
        jwks_server.server_close()
        jwks_thread.join(timeout=5)

    expected = {
        "missing_bearer_rejected": lambda item: item["status_code"] == 401,
        "wrong_audience_rejected": lambda item: item["status_code"] == 401,
        "invalid_signature_rejected": lambda item: item["status_code"] == 401,
        "authorized_session_create": lambda item: item["status_code"] == 200
        and item["tenant_id"] == "tenant-jwks"
        and item["session_id_present"],
        "authorized_document_create_grants_acl": lambda item: item["status_code"] == 200
        and item["tenant_id"] == "tenant-jwks"
        and item["document_id"] == "doc-jwks",
        "authorized_document_list_sees_created_doc": lambda item: item["status_code"] == 200
        and "doc-jwks" in item["document_ids"],
        "authorized_audit_list_tenant_scoped": lambda item: item["status_code"] == 200
        and item["tenant_ids"] == ["tenant-jwks"]
        and {"document_create", "document_list"}.issubset(item["event_types"]),
        "jwks_endpoint_was_used": lambda item: item["request_count"] >= 1
        and "/.well-known/jwks.json" in item["paths"],
    }
    for check in checks:
        check["passed"] = expected[check["name"]](check)
    evidence = {
        "schema": "doge.doged_enterprise_jwks_auth_smoke.v1",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "result": "passed" if all(item["passed"] for item in checks) else "failed",
        "base_url": base_url,
        "auth_mode": "enterprise",
        "provider": "local_jwks_fixture",
        "issuer": ISSUER,
        "audience": AUDIENCE,
        "jwks_url": jwks_url,
        "checks": checks,
        "process": {
            "returncode": process.returncode if process is not None else None,
            "shutdown_requested_by_smoke": True,
            "forced_shutdown": forced_shutdown,
            "stdout_tail": stdout[-1000:],
            "stderr_tail": stderr[-2000:],
        },
    }
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    if evidence["result"] != "passed":
        raise SystemExit(f"doged enterprise JWKS auth smoke failed; see {evidence_path}")
    return evidence


def _token(private_key: rsa.RSAPrivateKey, overrides: dict[str, Any]) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "sub": "operator@example.test",
        "tenant_id": "tenant-jwks",
        "roles": ["tenant_admin", "portfolio_manager"],
        "entitlements": ["enterprise_acl_admin", "risk", "evidence"],
        "approval_authority": ["publish-memo"],
        "document_acl": ["doc-jwks"],
        "portfolio_permission": ["portfolio-jwks"],
        "data_classification": "confidential",
        "project_id": "project-jwks",
        "jti": "jwks-smoke",
    }
    claims.update(overrides)
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": KEY_ID})


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local doged enterprise OIDC/JWKS auth smoke.")
    parser.add_argument("--output-dir", default="production/qa/evidence/manual", help="Directory for JSON evidence.")
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    args = parser.parse_args()
    evidence = _run(args)
    print(json.dumps({"result": evidence["result"], "checks": evidence["checks"]}, indent=2))


if __name__ == "__main__":
    main()

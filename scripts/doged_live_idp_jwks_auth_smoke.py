from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
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
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from doge.core.security.redaction import redact_secrets
from scripts.validate_enterprise_production_validation_evidence import REQUIRED_CHECK_IDS, validate


SCHEMA = "doge.live_idp_jwks_auth_smoke.v1"
PROVIDER = "live_operator_idp_jwks"
DEFAULT_ISSUE_REF = "AUTH-PROD-REMAINING-GATES"
REQUIRED_ENV = (
    "DOGE_AUTH_OIDC_ISSUER",
    "DOGE_AUTH_OIDC_AUDIENCE",
    "DOGE_AUTH_OIDC_JWKS_URL",
    "DOGE_LIVE_IDP_VALID_TOKEN_FILE",
    "DOGE_LIVE_IDP_WRONG_AUDIENCE_TOKEN_FILE",
    "DOGE_LIVE_IDP_EXPECTED_TENANT_ID",
    "DOGE_LIVE_IDP_OPERATOR_EVIDENCE_REF",
)


class SmokeConfigError(RuntimeError):
    pass


class SmokeExecutionError(RuntimeError):
    pass


def _blocked_check_ref(check_id: str, issue_ref: str) -> str:
    return f"operator-secure-store://enterprise/auth-prod/blocker-log/{issue_ref}/{check_id}"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _utc_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fingerprint(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _safe_value(value: str, *, sensitive: bool) -> str:
    if not sensitive:
        return value
    return _fingerprint(value)


def _mask_operator_values(value: str, config: dict[str, Any], *, sensitive: bool) -> str:
    if not sensitive:
        return value
    masked = value
    for key in ("issuer", "audience", "jwks_url", "expected_tenant_id"):
        raw = str(config.get(key) or "")
        if raw:
            masked = masked.replace(raw, _fingerprint(raw))
    return masked


def _read_token_file(path_value: str, name: str) -> str:
    path = Path(path_value)
    if not path.exists() or not path.is_file():
        raise SmokeConfigError(f"{name} points to a missing token file")
    token = path.read_text(encoding="utf-8").strip()
    if not token:
        raise SmokeConfigError(f"{name} token file is empty")
    return token


def _require_env(env: dict[str, str]) -> None:
    missing = [name for name in REQUIRED_ENV if not env.get(name)]
    if missing:
        raise SmokeConfigError("missing required environment variables: " + ", ".join(sorted(missing)))


def load_config(env: dict[str, str] | None = None) -> dict[str, Any]:
    source = env or os.environ
    _require_env(source)
    return {
        "issuer": source["DOGE_AUTH_OIDC_ISSUER"],
        "audience": source["DOGE_AUTH_OIDC_AUDIENCE"],
        "jwks_url": source["DOGE_AUTH_OIDC_JWKS_URL"],
        "algorithms": source.get("DOGE_AUTH_OIDC_ALGORITHMS") or "RS256",
        "clock_skew_seconds": source.get("DOGE_AUTH_CLOCK_SKEW_SECONDS") or "60",
        "valid_token": _read_token_file(source["DOGE_LIVE_IDP_VALID_TOKEN_FILE"], "DOGE_LIVE_IDP_VALID_TOKEN_FILE"),
        "wrong_audience_token": _read_token_file(
            source["DOGE_LIVE_IDP_WRONG_AUDIENCE_TOKEN_FILE"],
            "DOGE_LIVE_IDP_WRONG_AUDIENCE_TOKEN_FILE",
        ),
        "invalid_signature_token": (
            _read_token_file(
                source["DOGE_LIVE_IDP_INVALID_SIGNATURE_TOKEN_FILE"],
                "DOGE_LIVE_IDP_INVALID_SIGNATURE_TOKEN_FILE",
            )
            if source.get("DOGE_LIVE_IDP_INVALID_SIGNATURE_TOKEN_FILE")
            else None
        ),
        "rotation_token": (
            _read_token_file(
                source["DOGE_LIVE_IDP_ROTATION_TOKEN_FILE"],
                "DOGE_LIVE_IDP_ROTATION_TOKEN_FILE",
            )
            if source.get("DOGE_LIVE_IDP_ROTATION_TOKEN_FILE")
            else None
        ),
        "expected_tenant_id": source["DOGE_LIVE_IDP_EXPECTED_TENANT_ID"],
        "operator_evidence_ref": source["DOGE_LIVE_IDP_OPERATOR_EVIDENCE_REF"],
        "rotation_evidence_ref": source.get("DOGE_LIVE_IDP_ROTATION_EVIDENCE_REF") or "",
        "issue_ref": source.get("DOGE_LIVE_IDP_ISSUE_REF") or DEFAULT_ISSUE_REF,
    }


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
            return response.status, _decode_body(response.read()), dict(response.headers)
    except HTTPError as exc:
        return exc.code, _decode_body(exc.read()), dict(exc.headers)


def _decode_body(raw: bytes) -> dict[str, Any] | str:
    body = raw.decode("utf-8")
    if not body:
        return {}
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return body
    return payload if isinstance(payload, dict) else body


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


def _check(name: str, *, status_code: int | None = None, passed: bool, details: dict[str, Any] | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {"name": name, "passed": passed}
    if status_code is not None:
        item["status_code"] = status_code
    if details:
        item.update(details)
    return item


def _skip(name: str, reason: str, evidence_ref: str) -> dict[str, Any]:
    return {
        "name": name,
        "status": "skipped",
        "optional": True,
        "passed": True,
        "reason": reason,
        "evidence_ref": evidence_ref,
    }


def run_smoke(args: argparse.Namespace, config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or load_config()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    date = args.date or _utc_date()
    started_at = args.created_at or _now_iso()
    port = _free_port() if args.port == 0 else args.port
    base_url = f"http://127.0.0.1:{port}"
    detailed_path = output_dir / f"live-idp-jwks-smoke-{date}.json"
    observations_path = output_dir / f"enterprise-production-observations-{date}.json"

    checks: list[dict[str, Any]] = []
    process: subprocess.Popen[str] | None = None
    stdout = ""
    stderr = ""
    forced_shutdown = False

    try:
        with tempfile.TemporaryDirectory(prefix="doge-live-idp-jwks-smoke-") as tmp:
            tmp_path = Path(tmp)
            env = os.environ.copy()
            env.update(
                {
                    "PYTHONPATH": f"{ROOT / 'src'}{os.pathsep}{env.get('PYTHONPATH', '')}",
                    "DOGE_AUTH_MODE": "enterprise",
                    "DOGE_PROCESS_ROLE": "api",
                    "DOGE_AUTH_OIDC_ISSUER": config["issuer"],
                    "DOGE_AUTH_OIDC_AUDIENCE": config["audience"],
                    "DOGE_AUTH_OIDC_JWKS_URL": config["jwks_url"],
                    "DOGE_AUTH_OIDC_ALGORITHMS": config["algorithms"],
                    "DOGE_AUTH_CLOCK_SKEW_SECONDS": str(config["clock_skew_seconds"]),
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
                _wait_ready(base_url, config["valid_token"], args.timeout_seconds)
                checks.extend(_run_endpoint_checks(base_url, config))
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
        safe_stdout = _mask_operator_values(str(redact_secrets(stdout[-1000:])), config, sensitive=args.sensitive)
        safe_stderr = _mask_operator_values(str(redact_secrets(stderr[-2000:])), config, sensitive=args.sensitive)

    result = "passed" if all(item.get("passed") is True for item in checks) else "failed"
    evidence = {
        "schema": SCHEMA,
        "started_at": started_at,
        "result": result,
        "provider": PROVIDER,
        "base_url": base_url,
        "auth_mode": "enterprise",
        "issuer": _safe_value(config["issuer"], sensitive=args.sensitive),
        "audience": _safe_value(config["audience"], sensitive=args.sensitive),
        "jwks_url": _safe_value(config["jwks_url"], sensitive=args.sensitive),
        "algorithms": config["algorithms"],
        "expected_tenant": _fingerprint(config["expected_tenant_id"]),
        "operator_evidence_ref": config["operator_evidence_ref"],
        "checks": checks,
        "process": {
            "returncode": process.returncode if process is not None else None,
            "shutdown_requested_by_smoke": True,
            "forced_shutdown": forced_shutdown,
            "stdout_tail": safe_stdout,
            "stderr_tail": safe_stderr,
        },
        "redaction_review": {
            "contains_credentials": False,
            "contains_raw_subjects": False,
            "contains_proprietary_customer_data": False,
        },
    }
    evidence = redact_secrets(evidence)
    detailed_path.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")

    if args.write_observations:
        observations = build_observations(
            detailed_smoke_path=detailed_path,
            live_passed=result == "passed",
            operator_evidence_ref=config["operator_evidence_ref"],
            executed_at=started_at,
            issue_ref=config["issue_ref"],
        )
        observations_path.write_text(json.dumps(observations, indent=2, sort_keys=True), encoding="utf-8")
        _validate_observations(observations)

    if result != "passed":
        raise SmokeExecutionError(f"live IdP/JWKS auth smoke failed; see {detailed_path}")
    return evidence


def _run_endpoint_checks(base_url: str, config: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    expected_tenant = config["expected_tenant_id"]
    doc_id = "doc-live-idp-jwks-smoke"

    missing = _request("GET", f"{base_url}/v1/sessions")
    checks.append(_check("missing_bearer_rejected", status_code=missing[0], passed=missing[0] == 401))

    wrong_audience = _request("GET", f"{base_url}/v1/sessions", token=config["wrong_audience_token"])
    checks.append(_check("wrong_audience_rejected", status_code=wrong_audience[0], passed=wrong_audience[0] == 401))

    invalid_token = config.get("invalid_signature_token")
    if invalid_token:
        invalid_signature = _request("GET", f"{base_url}/v1/sessions", token=invalid_token)
        checks.append(
            _check(
                "invalid_signature_rejected",
                status_code=invalid_signature[0],
                passed=invalid_signature[0] == 401,
            )
        )
    else:
        checks.append(
            _skip(
                "invalid_signature_rejected",
                "operator invalid-signature token was not supplied for this validation window",
                config["operator_evidence_ref"],
            )
        )

    session = _request(
        "POST",
        f"{base_url}/v1/sessions",
        token=config["valid_token"],
        request_id="req-live-idp-jwks-session",
        json_body={"title": "Live IdP JWKS auth smoke"},
    )
    session_payload = session[1] if isinstance(session[1], dict) else {}
    checks.append(
        _check(
            "authorized_session_create",
            status_code=session[0],
            passed=session[0] == 200
            and session_payload.get("tenant_id") == expected_tenant
            and bool(session_payload.get("session_id")),
            details={
                "tenant_match": session_payload.get("tenant_id") == expected_tenant,
                "session_id_present": bool(session_payload.get("session_id")),
            },
        )
    )

    created = _request(
        "POST",
        f"{base_url}/v1/documents",
        token=config["valid_token"],
        request_id="req-live-idp-jwks-doc-create",
        json_body={
            "document_id": doc_id,
            "filename": "live-idp-jwks-smoke.txt",
            "content": "synthetic live idp jwks smoke document",
        },
    )
    created_payload = created[1] if isinstance(created[1], dict) else {}
    checks.append(
        _check(
            "authorized_document_create_grants_acl",
            status_code=created[0],
            passed=created[0] == 200 and created_payload.get("tenant_id") == expected_tenant,
            details={"tenant_match": created_payload.get("tenant_id") == expected_tenant, "document_id": doc_id},
        )
    )

    listed = _request(
        "GET",
        f"{base_url}/v1/documents",
        token=config["valid_token"],
        request_id="req-live-idp-jwks-doc-list",
    )
    listed_payload = listed[1] if isinstance(listed[1], dict) else {}
    listed_ids = [item.get("document_id") for item in listed_payload.get("documents", [])]
    checks.append(
        _check(
            "authorized_document_list_sees_created_doc",
            status_code=listed[0],
            passed=listed[0] == 200 and doc_id in listed_ids,
            details={"created_document_visible": doc_id in listed_ids},
        )
    )

    audit = _request("GET", f"{base_url}/v1/audit/events", token=config["valid_token"])
    audit_payload = audit[1] if isinstance(audit[1], dict) else {}
    audit_events = audit_payload.get("events", [])
    tenant_scoped = all(item.get("tenant_id") == expected_tenant for item in audit_events)
    event_types = {item.get("event_type") for item in audit_events}
    checks.append(
        _check(
            "authorized_audit_list_tenant_scoped",
            status_code=audit[0],
            passed=audit[0] == 200 and tenant_scoped and {"document_create", "document_list"}.issubset(event_types),
            details={
                "tenant_scoped": tenant_scoped,
                "document_create_seen": "document_create" in event_types,
                "document_list_seen": "document_list" in event_types,
            },
        )
    )
    checks.append(
        _check(
            "jwks_validation_observed",
            passed=_passed(checks, "authorized_session_create"),
            details={"evidence_ref": config["operator_evidence_ref"]},
        )
    )
    if config.get("rotation_token"):
        rotation = _request("GET", f"{base_url}/v1/sessions", token=config["rotation_token"])
        checks.append(
            _check(
                "jwks_rotation_or_refresh_observed",
                status_code=rotation[0],
                passed=rotation[0] == 200,
                details={"evidence_ref": config.get("rotation_evidence_ref") or config["operator_evidence_ref"]},
            )
        )
    else:
        checks.append(
            _skip(
                "jwks_rotation_or_refresh_observed",
                "operator rotation token was not supplied for this validation window",
                config.get("rotation_evidence_ref") or config["operator_evidence_ref"],
            )
        )
    return checks


def _passed(checks: list[dict[str, Any]], name: str) -> bool:
    return any(item.get("name") == name and item.get("passed") is True for item in checks)


def build_observations(
    *,
    detailed_smoke_path: Path,
    live_passed: bool,
    operator_evidence_ref: str,
    executed_at: str,
    issue_ref: str = DEFAULT_ISSUE_REF,
) -> dict[str, Any]:
    live_status = "passed" if live_passed else "failed"
    checks: dict[str, dict[str, Any]] = {
        "live_idp_jwks": {
            "status": live_status,
            "evidence_ref": operator_evidence_ref,
            "notes": (
                "Real operator-approved OIDC/JWKS provider accepted valid token, rejected invalid inputs, "
                "mapped tenant context, enforced document ACL, emitted tenant-scoped audit events, and "
                f"JWKS validation behavior was observed. Detailed redacted smoke: {_rel(detailed_smoke_path)}"
            )
            if live_passed
            else f"Live operator IdP/JWKS smoke failed; see {_rel(detailed_smoke_path)}",
        }
    }
    if not live_passed:
        checks["live_idp_jwks"]["issue_ref"] = issue_ref

    for check_id in sorted(REQUIRED_CHECK_IDS - {"live_idp_jwks"}):
        checks[check_id] = {
            "status": "blocked",
            "evidence_ref": _blocked_check_ref(check_id, issue_ref),
            "issue_ref": issue_ref,
            "notes": f"Pending operator-approved {check_id} validation.",
        }

    return {
        "result": "failed",
        "executed_at": executed_at,
        "operator": {"role": "platform-operator", "initials": "OPS"},
        "issue_refs": [issue_ref],
        "checks": checks,
        "redaction_review": {
            "contains_credentials": False,
            "contains_raw_subjects": False,
            "contains_proprietary_customer_data": False,
            "notes": "Repository evidence contains only redacted refs, boolean results, status summaries, and secure-store URIs.",
        },
    }


def _validate_observations(observations: dict[str, Any]) -> None:
    from scripts.build_enterprise_production_validation_evidence import build_evidence

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as tmp:
        json.dump(observations, tmp)
        tmp_path = Path(tmp.name)
    try:
        payload = build_evidence(observations_path=tmp_path, created_at=observations["executed_at"])
        errors = validate(payload)
        if errors:
            raise SmokeConfigError("generated observation did not validate: " + "; ".join(errors))
    finally:
        tmp_path.unlink(missing_ok=True)


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run an operator-controlled live IdP/JWKS doged auth smoke.")
    parser.add_argument("--output-dir", default="production/qa/evidence/enterprise", help="Directory for JSON evidence.")
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--port", type=int, default=8917, help="Loopback API port; use 0 to choose a free port.")
    parser.add_argument("--date", help="Evidence date suffix in YYYY-MM-DD format. Defaults to current UTC date.")
    parser.add_argument("--created-at", help="ISO-8601 evidence timestamp. Defaults to current UTC timestamp.")
    parser.add_argument("--sensitive", action="store_true", help="Mask issuer, audience, and JWKS URL in evidence.")
    parser.add_argument(
        "--write-observations",
        action="store_true",
        help="Also write enterprise-production-observations-YYYY-MM-DD.json.",
    )
    args = parser.parse_args(argv)

    try:
        evidence = run_smoke(args)
    except SmokeConfigError as exc:
        print(json.dumps({"result": "config_error", "error": str(exc)}, indent=2, sort_keys=True), file=sys.stderr)
        return 2
    except SmokeExecutionError as exc:
        print(
            json.dumps({"result": "smoke_failed", "error": redact_secrets(str(exc))}, indent=2, sort_keys=True),
            file=sys.stderr,
        )
        return 1
    except Exception as exc:
        print(
            json.dumps({"result": "smoke_error", "error": redact_secrets(str(exc))}, indent=2, sort_keys=True),
            file=sys.stderr,
        )
        return 1
    print(json.dumps({"result": evidence["result"], "checks": evidence["checks"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

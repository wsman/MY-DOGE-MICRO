from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from doge.core.security.redaction import redact_secrets
from scripts import doged_live_idp_jwks_auth_smoke as live_smoke


INSPECTION_SCHEMA = "doge.idp_jwks_operator_tool.jwks_inspection.v1"
DEFAULT_EVIDENCE_DIR = ROOT / "production" / "qa" / "evidence" / "enterprise"


class ToolConfigError(RuntimeError):
    pass


class ToolExecutionError(RuntimeError):
    pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _utc_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _fingerprint(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _safe_value(value: str, *, sensitive: bool) -> str:
    return _fingerprint(value) if sensitive else value


def _jwk_fingerprint(jwk: dict[str, Any]) -> str:
    rendered = json.dumps(jwk, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return _fingerprint(rendered)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _fetch_jwks(url: str, timeout_seconds: float) -> dict[str, Any]:
    request = Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise ToolExecutionError(f"JWKS endpoint returned HTTP {exc.code}") from exc
    except URLError as exc:
        raise ToolExecutionError(f"JWKS endpoint is not reachable: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise ToolExecutionError("JWKS endpoint did not return valid JSON") from exc
    if not isinstance(payload, dict):
        raise ToolExecutionError("JWKS endpoint response must be a JSON object")
    return payload


def jwks_inspect(args: argparse.Namespace) -> int:
    jwks = _fetch_jwks(args.jwks_url, args.timeout_seconds)
    keys = jwks.get("keys")
    if not isinstance(keys, list):
        keys = []

    requested_algorithms = _algorithm_set(args.algorithms)
    key_summaries: list[dict[str, Any]] = []
    errors: list[str] = []
    if not keys:
        errors.append("JWKS contains no keys")

    for index, item in enumerate(keys):
        if not isinstance(item, dict):
            errors.append(f"keys[{index}] must be an object")
            continue
        kid = item.get("kid")
        alg = item.get("alg")
        use = item.get("use")
        if not isinstance(kid, str) or not kid.strip():
            errors.append(f"keys[{index}] is missing kid")
        if alg is not None and alg not in requested_algorithms:
            errors.append(f"keys[{index}] declares unsupported alg {alg}")
        if use is not None and use != "sig":
            errors.append(f"keys[{index}] declares unsupported use {use}")
        key_summaries.append(
            {
                "index": index,
                "fingerprint": _jwk_fingerprint(item),
                "kid_fingerprint": _fingerprint(kid) if isinstance(kid, str) and kid else None,
                "kid_present": isinstance(kid, str) and bool(kid.strip()),
                "kty": item.get("kty"),
                "alg": alg,
                "use": use,
            }
        )

    payload = {
        "schema": INSPECTION_SCHEMA,
        "created_at": args.created_at or _now_iso(),
        "result": "passed" if not errors else "failed",
        "issuer": _safe_value(args.issuer, sensitive=args.sensitive),
        "audience": _safe_value(args.audience, sensitive=args.sensitive),
        "jwks_url": _safe_value(args.jwks_url, sensitive=args.sensitive),
        "algorithms_requested": sorted(requested_algorithms),
        "key_count": len(keys),
        "keys": key_summaries,
        "errors": errors,
        "redaction_review": {
            "contains_credentials": False,
            "contains_raw_subjects": False,
            "contains_proprietary_customer_data": False,
            "notes": "JWKS inspection evidence stores key fingerprints only; full key material is not persisted.",
        },
    }
    output = Path(args.output) if args.output else None
    if output:
        _write_json(output, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not errors else 1


def _algorithm_set(value: str) -> set[str]:
    algorithms = {item.strip() for item in value.split(",") if item.strip()}
    if not algorithms:
        raise ToolConfigError("at least one OIDC algorithm must be supplied")
    return algorithms


def env_template(args: argparse.Namespace) -> int:
    lines = [
        "# Operator-controlled MY-DOGE live IdP/JWKS smoke environment.",
        "# Keep token files outside the repository and never paste token values into this template.",
        f"$env:DOGE_AUTH_OIDC_ISSUER = {_ps(args.issuer)}",
        f"$env:DOGE_AUTH_OIDC_AUDIENCE = {_ps(args.audience)}",
        f"$env:DOGE_AUTH_OIDC_JWKS_URL = {_ps(args.jwks_url)}",
        f"$env:DOGE_AUTH_OIDC_ALGORITHMS = {_ps(args.algorithms)}",
        f"$env:DOGE_AUTH_CLOCK_SKEW_SECONDS = {_ps(str(args.clock_skew_seconds))}",
        f"$env:DOGE_LIVE_IDP_VALID_TOKEN_FILE = {_ps(args.valid_token_file)}",
        f"$env:DOGE_LIVE_IDP_WRONG_AUDIENCE_TOKEN_FILE = {_ps(args.wrong_audience_token_file)}",
        f"$env:DOGE_LIVE_IDP_EXPECTED_TENANT_ID = {_ps(args.expected_tenant_id)}",
        f"$env:DOGE_LIVE_IDP_OPERATOR_EVIDENCE_REF = {_ps(args.operator_evidence_ref)}",
    ]
    if args.invalid_signature_token_file:
        lines.append(f"$env:DOGE_LIVE_IDP_INVALID_SIGNATURE_TOKEN_FILE = {_ps(args.invalid_signature_token_file)}")
    if args.rotation_token_file:
        lines.append(f"$env:DOGE_LIVE_IDP_ROTATION_TOKEN_FILE = {_ps(args.rotation_token_file)}")
    if args.rotation_evidence_ref:
        lines.append(f"$env:DOGE_LIVE_IDP_ROTATION_EVIDENCE_REF = {_ps(args.rotation_evidence_ref)}")
    if args.issue_ref:
        lines.append(f"$env:DOGE_LIVE_IDP_ISSUE_REF = {_ps(args.issue_ref)}")
    rendered = "\n".join(lines) + "\n"

    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
        print(json.dumps({"result": "passed", "output": str(path)}, indent=2, sort_keys=True))
    else:
        print(rendered, end="")
    return 0


def _ps(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def make_invalid_signature(args: argparse.Namespace) -> int:
    source_path = Path(args.like_token_file)
    if not source_path.exists() or not source_path.is_file():
        raise ToolConfigError("like-token-file points to a missing token file")
    source_token = source_path.read_text(encoding="utf-8").strip()
    if not source_token:
        raise ToolConfigError("like-token-file is empty")

    try:
        header = jwt.get_unverified_header(source_token)
        claims = jwt.decode(
            source_token,
            options={
                "verify_signature": False,
                "verify_aud": False,
                "verify_exp": False,
                "verify_iat": False,
                "verify_nbf": False,
            },
        )
    except jwt.PyJWTError as exc:
        raise ToolConfigError(f"like-token-file does not contain a readable JWT: {exc}") from exc

    signing_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    output_header = {
        "kid": header.get("kid") or "doge-operator-invalid-signature",
        "typ": header.get("typ") or "JWT",
    }
    token = jwt.encode(claims, signing_key, algorithm=args.algorithm, headers=output_header)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(token + "\n", encoding="utf-8")
    summary = {
        "result": "passed",
        "output": str(output_path),
        "algorithm": args.algorithm,
        "source_token_fingerprint": _fingerprint(source_token),
        "output_token_fingerprint": _fingerprint(token),
        "kid_fingerprint": _fingerprint(str(output_header["kid"])),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def run_smoke(args: argparse.Namespace) -> int:
    try:
        live_smoke.load_config(os.environ)
    except live_smoke.SmokeConfigError as exc:
        raise ToolConfigError(str(exc)) from exc

    command = [
        sys.executable,
        str(ROOT / "scripts" / "doged_live_idp_jwks_auth_smoke.py"),
        "--output-dir",
        args.output_dir,
        "--timeout-seconds",
        str(args.timeout_seconds),
        "--port",
        str(args.port),
        "--write-observations",
    ]
    if not args.no_sensitive:
        command.append("--sensitive")
    if args.date:
        command.extend(["--date", args.date])
    if args.created_at:
        command.extend(["--created-at", args.created_at])
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    _write_process_output(result.stdout, result.stderr)
    return result.returncode


def build_evidence(args: argparse.Namespace) -> int:
    command = [
        sys.executable,
        str(ROOT / "scripts" / "build_enterprise_production_validation_evidence.py"),
        "--observations",
        args.observations,
        "--output",
        args.output,
    ]
    if args.created_at:
        command.extend(["--created-at", args.created_at])
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    _write_process_output(result.stdout, result.stderr)
    return result.returncode


def _write_process_output(stdout: str, stderr: str) -> None:
    safe_stdout = str(redact_secrets(stdout))
    safe_stderr = str(redact_secrets(stderr))
    if safe_stdout:
        sys.stdout.write(safe_stdout)
        if not safe_stdout.endswith("\n"):
            sys.stdout.write("\n")
    if safe_stderr:
        sys.stderr.write(safe_stderr)
        if not safe_stderr.endswith("\n"):
            sys.stderr.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Operator-controlled IdP/JWKS JWT validation and evidence tool.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("jwks-inspect", help="Inspect a live JWKS endpoint without persisting keys.")
    inspect_parser.add_argument("--issuer", required=True)
    inspect_parser.add_argument("--audience", required=True)
    inspect_parser.add_argument("--jwks-url", required=True)
    inspect_parser.add_argument("--algorithms", default="RS256")
    inspect_parser.add_argument("--timeout-seconds", type=float, default=10.0)
    inspect_parser.add_argument("--created-at")
    inspect_parser.add_argument("--output")
    inspect_parser.add_argument("--sensitive", action="store_true", help="Fingerprint issuer, audience, and JWKS URL.")
    inspect_parser.set_defaults(func=jwks_inspect)

    env_parser = subparsers.add_parser("env-template", help="Render a PowerShell env template for operator execution.")
    env_parser.add_argument("--issuer", required=True)
    env_parser.add_argument("--audience", required=True)
    env_parser.add_argument("--jwks-url", required=True)
    env_parser.add_argument("--algorithms", default="RS256")
    env_parser.add_argument("--clock-skew-seconds", type=int, default=60)
    env_parser.add_argument("--valid-token-file", required=True)
    env_parser.add_argument("--wrong-audience-token-file", required=True)
    env_parser.add_argument("--invalid-signature-token-file")
    env_parser.add_argument("--rotation-token-file")
    env_parser.add_argument("--expected-tenant-id", required=True)
    env_parser.add_argument("--operator-evidence-ref", required=True)
    env_parser.add_argument("--rotation-evidence-ref")
    env_parser.add_argument("--issue-ref")
    env_parser.add_argument("--output")
    env_parser.set_defaults(func=env_template)

    invalid_parser = subparsers.add_parser(
        "make-invalid-signature",
        help="Create a JWT-shaped negative fixture signed by a throwaway key.",
    )
    invalid_parser.add_argument("--like-token-file", required=True)
    invalid_parser.add_argument("--output", required=True)
    invalid_parser.add_argument("--algorithm", default="RS256", choices=["RS256", "RS384", "RS512"])
    invalid_parser.set_defaults(func=make_invalid_signature)

    smoke_parser = subparsers.add_parser("run-smoke", help="Validate env and run the existing live doged smoke.")
    smoke_parser.add_argument("--output-dir", default=str(DEFAULT_EVIDENCE_DIR))
    smoke_parser.add_argument("--timeout-seconds", type=float, default=30.0)
    smoke_parser.add_argument("--port", type=int, default=8917)
    smoke_parser.add_argument("--date", default=_utc_date())
    smoke_parser.add_argument("--created-at")
    smoke_parser.add_argument("--no-sensitive", action="store_true", help="Do not mask issuer/audience/JWKS URL.")
    smoke_parser.set_defaults(func=run_smoke)

    evidence_parser = subparsers.add_parser("build-evidence", help="Build and validate enterprise production evidence.")
    evidence_parser.add_argument(
        "--observations",
        default=str(DEFAULT_EVIDENCE_DIR / f"enterprise-production-observations-{_utc_date()}.json"),
    )
    evidence_parser.add_argument(
        "--output",
        default=str(DEFAULT_EVIDENCE_DIR / f"enterprise-production-validation-{_utc_date()}.json"),
    )
    evidence_parser.add_argument("--created-at")
    evidence_parser.set_defaults(func=build_evidence)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except ToolConfigError as exc:
        print(json.dumps({"result": "config_error", "error": str(exc)}, indent=2, sort_keys=True), file=sys.stderr)
        return 2
    except ToolExecutionError as exc:
        print(
            json.dumps({"result": "execution_error", "error": str(redact_secrets(str(exc)))}, indent=2, sort_keys=True),
            file=sys.stderr,
        )
        return 1
    except Exception as exc:
        print(
            json.dumps({"result": "tool_error", "error": str(redact_secrets(str(exc)))}, indent=2, sort_keys=True),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

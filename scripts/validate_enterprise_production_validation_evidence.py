from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.evidence_placeholders import placeholder_errors
from scripts.evidence_redaction import secret_leak_errors

SCHEMA = "doge.enterprise_production_validation.v1"
STORY_ID = "S017-004"
REQUIRED_CHECK_IDS = {
    "live_idp_jwks",
    "production_secret_store_command",
    "siem_worm_export",
    "live_remote_bind_deployment",
    "production_data_isolation_review",
}
SECRET_VALUE_PATTERNS = [
    re.compile(r"Bearer\s+(?=[A-Za-z0-9._~+/=-]*[._~+/=-])[A-Za-z0-9._~+/=-]{8,}", re.I),
    re.compile(r"\bsk-[A-Za-z0-9._-]{6,}\b", re.I),
    re.compile(r"\bAKIA[0-9A-Z]{12,}\b"),
]


def validate(payload: dict[str, Any], *, allow_template: bool = False) -> list[str]:
    errors: list[str] = []
    if payload.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA}")
    if payload.get("story_id") != STORY_ID:
        errors.append(f"story_id must be {STORY_ID}")
    _require_timestamp(payload.get("created_at"), "created_at", errors)

    result = payload.get("result")
    if result not in {"passed", "failed", "not_run"}:
        errors.append("result must be passed, failed, or not_run")
    if result == "not_run" and not allow_template:
        errors.append("not_run evidence is an enterprise production validation template/preflight artifact")
    if result in {"passed", "failed"}:
        errors.extend(placeholder_errors(payload))
        errors.extend(secret_leak_errors(payload))

    errors.extend(_validate_local_evidence(_dict(payload.get("local_evidence"))))

    checks = payload.get("checks")
    if not isinstance(checks, list):
        errors.append("checks must be a list")
        checks = []
    check_map = {
        item.get("id"): item
        for item in checks
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    missing = REQUIRED_CHECK_IDS - set(check_map)
    extra = set(check_map) - REQUIRED_CHECK_IDS
    if missing:
        errors.append(f"missing checks: {', '.join(sorted(missing))}")
    if extra:
        errors.append(f"unexpected checks: {', '.join(sorted(extra))}")

    for item in checks:
        if not isinstance(item, dict):
            errors.append("each check must be an object")
            continue
        _validate_check(item, result, errors)

    operator = _dict(payload.get("operator"))
    if result in {"passed", "failed"}:
        _require_non_empty(operator.get("role"), "operator.role", errors)
        _require_non_empty(operator.get("initials"), "operator.initials", errors)
        _require_timestamp(payload.get("executed_at"), "executed_at", errors)

    if result == "passed":
        for check_id, item in check_map.items():
            if item.get("status") != "passed":
                errors.append(f"{check_id}: passed evidence requires every check to pass")
    if result == "failed" and not payload.get("issue_refs"):
        errors.append("failed evidence requires issue_refs")

    redaction = _dict(payload.get("redaction_review"))
    for key in ["contains_credentials", "contains_raw_subjects", "contains_proprietary_customer_data"]:
        if redaction.get(key) is True:
            errors.append(f"redaction_review.{key} must be false")
    if _contains_secret(payload):
        errors.append("evidence appears to contain a bearer token, provider key, cloud access key, or credential")

    return errors


def _validate_check(item: dict[str, Any], result: Any, errors: list[str]) -> None:
    check_id = item.get("id")
    status = item.get("status")
    if status not in {"passed", "failed", "blocked", "not_run"}:
        errors.append(f"{check_id}: status must be passed, failed, blocked, or not_run")
    required_evidence = item.get("required_evidence")
    if not isinstance(required_evidence, list) or not required_evidence:
        errors.append(f"{check_id}: required_evidence must be a non-empty list")
    if result in {"passed", "failed"}:
        _require_non_empty(item.get("evidence_ref"), f"{check_id}.evidence_ref", errors)
    if result == "failed" and status in {"failed", "blocked"} and not item.get("issue_ref"):
        errors.append(f"{check_id}: failed/blocked check requires issue_ref")


def _validate_local_evidence(evidence: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_paths = {
        "enterprise_auth_plan",
        "operational_audit_review",
        "audit_siem_worm_handoff_packet",
        "production_secret_store_selection",
        "local_jwks_smoke",
        "local_process_secret_smoke",
        "local_remote_bind_gate_smoke",
    }
    missing = required_paths - set(evidence)
    if missing:
        errors.append(f"missing local_evidence refs: {', '.join(sorted(missing))}")
    for key, value in evidence.items():
        if not isinstance(value, str) or not value.strip():
            errors.append(f"local_evidence.{key} must be a non-empty path")
            continue
        path = ROOT / value
        if not path.exists():
            errors.append(f"local evidence not found: {value}")
            continue
        if path.suffix == ".json":
            item = json.loads(path.read_text(encoding="utf-8"))
            if item.get("result") not in {None, "passed"}:
                errors.append(f"local evidence {value} must be passed when it has result")
            summary = _dict(item.get("summary"))
            if summary and summary.get("passed") is not True:
                errors.append(f"local evidence {value} summary must be passed")
    return errors


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _require_non_empty(value: Any, field: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field} is required")


def _require_timestamp(value: Any, field: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field} is required")
        return
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{field} must be ISO-8601")


def _contains_secret(payload: dict[str, Any]) -> bool:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return any(pattern.search(text) for pattern in SECRET_VALUE_PATTERNS)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate S017 enterprise production validation evidence JSON.")
    parser.add_argument("evidence", help="Path to enterprise production validation evidence JSON.")
    parser.add_argument("--allow-template", action="store_true", help="Allow result=not_run template evidence.")
    args = parser.parse_args(argv)

    path = Path(args.evidence)
    payload = json.loads(path.read_text(encoding="utf-8"))
    errors = validate(payload, allow_template=args.allow_template)
    result = {"path": str(path), "passed": not errors, "errors": errors}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

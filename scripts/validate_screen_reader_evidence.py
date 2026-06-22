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


SCHEMA = "doge.research_agent_screen_reader_manual.v1"
REQUIRED_CHECK_IDS = {
    "sr_landmarks_sections",
    "sr_keyboard_primary_controls",
    "sr_status_announcements",
    "sr_approval_context",
    "sr_memo_evidence_quality_timeline",
    "sr_no_keyboard_trap",
}
SECRET_PATTERNS = [
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]+", re.I),
    re.compile(r"\bsk-[A-Za-z0-9._-]{6,}\b", re.I),
    re.compile(r"\b(api[_-]?key|secret|password|token)\s*[:=]\s*[^,\s}\]]+", re.I),
]


def validate(payload: dict[str, Any], *, allow_template: bool = False) -> list[str]:
    errors: list[str] = []
    if payload.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA}")
    if payload.get("story_id") != "S017-006":
        errors.append("story_id must be S017-006")
    _require_timestamp(payload.get("created_at"), "created_at", errors)

    result = payload.get("result")
    if result not in {"passed", "failed", "not_run"}:
        errors.append("result must be passed, failed, or not_run")
    if result == "not_run" and not allow_template:
        errors.append("not_run evidence is a template/preflight artifact, not a completed manual pass")
    if result in {"passed", "failed"}:
        errors.extend(placeholder_errors(payload))
        errors.extend(secret_leak_errors(payload))

    if result in {"passed", "failed"}:
        _require_timestamp(payload.get("executed_at"), "executed_at", errors)
        _require_non_empty(payload.get("summary"), "summary", errors)
        operator = _dict(payload.get("operator"))
        _require_non_empty(operator.get("role"), "operator.role", errors)
        _require_non_empty(operator.get("initials"), "operator.initials", errors)
        environment = _dict(payload.get("environment"))
        for key in ["platform", "browser", "browser_version", "screen_reader", "screen_reader_version", "web_url"]:
            _require_non_empty(environment.get(key), f"environment.{key}", errors)

    checks = payload.get("checks")
    if not isinstance(checks, list):
        errors.append("checks must be a list")
        checks = []
    check_ids = {item.get("id") for item in checks if isinstance(item, dict)}
    missing = REQUIRED_CHECK_IDS - check_ids
    extra = check_ids - REQUIRED_CHECK_IDS
    if missing:
        errors.append(f"missing checks: {', '.join(sorted(missing))}")
    if extra:
        errors.append(f"unexpected checks: {', '.join(sorted(str(item) for item in extra))}")

    for item in checks:
        if not isinstance(item, dict):
            errors.append("each check must be an object")
            continue
        status = item.get("status")
        if status not in {"passed", "failed", "blocked", "not_run"}:
            errors.append(f"{item.get('id')}: status must be passed, failed, blocked, or not_run")
        if result == "passed" and status != "passed":
            errors.append(f"{item.get('id')}: passed evidence requires every check to pass")
        if result == "failed" and status in {"failed", "blocked"} and not item.get("issue_ref"):
            errors.append(f"{item.get('id')}: failed/blocked check requires issue_ref")

    issues = payload.get("issues")
    if result == "failed" and not issues:
        errors.append("failed evidence requires at least one issue reference")
    if issues is not None and not isinstance(issues, list):
        errors.append("issues must be a list when present")

    redaction = _dict(payload.get("redaction_review"))
    if result in {"passed", "failed"}:
        _require_false(redaction.get("contains_secrets"), "redaction_review.contains_secrets", errors)
        _require_false(
            redaction.get("contains_sensitive_documents"),
            "redaction_review.contains_sensitive_documents",
            errors,
        )
    if _contains_secret(payload):
        errors.append("evidence appears to contain a bearer token, provider key, or key-value secret")

    return errors


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _require_non_empty(value: Any, field: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field} is required")


def _require_false(value: Any, field: str, errors: list[str]) -> None:
    if value is not False:
        errors.append(f"{field} must be false")


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
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate S017-006 screen-reader manual evidence JSON.")
    parser.add_argument("evidence", help="Path to screen-reader manual evidence JSON.")
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

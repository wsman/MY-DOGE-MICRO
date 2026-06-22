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

SCHEMA = "doge.sdk_release_approval.v1"
STORY_ID = "S017-007"
REQUIRED_LANGUAGES = {"python", "typescript"}
DECISION_STATUSES = {"approved", "needs_revision", "rejected", "not_decided"}
SECRET_PATTERNS = [
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]+", re.I),
    re.compile(r"\bsk-[A-Za-z0-9._-]{6,}\b", re.I),
    re.compile(r"\b(api[_-]?key|secret|password|token|credential)\s*[:=]\s*[^,\s}\]]+", re.I),
]


def validate(payload: dict[str, Any], *, allow_template: bool = False) -> list[str]:
    errors: list[str] = []
    if payload.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA}")
    if payload.get("story_id") != STORY_ID:
        errors.append(f"story_id must be {STORY_ID}")
    _require_timestamp(payload.get("created_at"), "created_at", errors)

    result = payload.get("result")
    if result not in {"approved", "needs_revision", "rejected", "not_run"}:
        errors.append("result must be approved, needs_revision, rejected, or not_run")
    if result == "not_run" and not allow_template:
        errors.append("not_run evidence is a release approval template/preflight artifact, not completed SDK release approval")
    if result in {"approved", "needs_revision", "rejected"}:
        errors.extend(placeholder_errors(payload))
        errors.extend(secret_leak_errors(payload))

    evidence = _dict(payload.get("local_evidence"))
    errors.extend(_validate_local_evidence(evidence))

    packages = payload.get("packages")
    if not isinstance(packages, list):
        errors.append("packages must be a list")
        packages = []
    package_map = {
        item.get("language"): item
        for item in packages
        if isinstance(item, dict) and isinstance(item.get("language"), str)
    }
    missing = REQUIRED_LANGUAGES - set(package_map)
    extra = set(package_map) - REQUIRED_LANGUAGES
    if missing:
        errors.append(f"missing packages: {', '.join(sorted(missing))}")
    if extra:
        errors.append(f"unexpected packages: {', '.join(sorted(extra))}")
    for item in packages:
        if not isinstance(item, dict):
            errors.append("each package must be an object")
            continue
        _validate_package(item, result, errors)

    manager = _dict(payload.get("release_manager"))
    if result in {"approved", "needs_revision", "rejected"}:
        _require_non_empty(manager.get("role"), "release_manager.role", errors)
        _require_non_empty(manager.get("initials"), "release_manager.initials", errors)
        _require_timestamp(payload.get("approved_at"), "approved_at", errors)

    if result == "approved":
        for language, item in package_map.items():
            if item.get("decision_status") != "approved":
                errors.append(f"{language}: approved evidence requires decision_status=approved")
        security = _dict(payload.get("security_review"))
        for key in [
            "no_credentials_in_package_config",
            "typescript_sources_excluded_from_tarball",
            "redaction_behavior_documented",
        ]:
            if security.get(key) is not True:
                errors.append(f"approved evidence requires security_review.{key}=true")

    if result in {"needs_revision", "rejected"} and not payload.get("issue_refs"):
        errors.append(f"{result} evidence requires issue_refs")

    security = _dict(payload.get("security_review"))
    if security.get("contains_credentials") is True:
        errors.append("security_review.contains_credentials must be false")
    if _contains_secret(payload):
        errors.append("evidence appears to contain a bearer token, provider key, or credential")

    return errors


def _validate_local_evidence(evidence: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ["package_compatibility", "release_packet", "external_consumer_smoke"]:
        value = evidence.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"local_evidence.{key} is required")
            continue
        path = ROOT / value
        if not path.exists():
            errors.append(f"local evidence not found: {value}")
    for key in ["python_wheel_local_smoke", "typescript_tarball_local_smoke"]:
        if evidence.get(key) is not True:
            errors.append(f"local_evidence.{key} must be true")

    smoke_path_value = evidence.get("external_consumer_smoke")
    if isinstance(smoke_path_value, str):
        smoke_path = ROOT / smoke_path_value
        if smoke_path.exists():
            smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
            if smoke.get("schema") != "doge.sdk_external_consumer_smoke.v1":
                errors.append("external consumer smoke schema is invalid")
            if _dict(smoke.get("summary")).get("passed") is not True:
                errors.append("external consumer smoke summary must be passed")
            check_names = {
                item.get("name")
                for item in smoke.get("checks", [])
                if isinstance(item, dict)
            }
            if check_names != {"python_sdk_external_consumer", "typescript_sdk_external_consumer"}:
                errors.append("external consumer smoke must include python and typescript consumer checks")
    return errors


def _validate_package(item: dict[str, Any], result: Any, errors: list[str]) -> None:
    language = item.get("language")
    status = item.get("decision_status")
    if status not in DECISION_STATUSES:
        errors.append(f"{language}: decision_status must be one of {', '.join(sorted(DECISION_STATUSES))}")
    for key in ["package_path", "current_name", "publish_guard"]:
        _require_non_empty(item.get(key), f"{language}.{key}", errors)

    if result == "approved":
        for key in [
            "approved_package_name",
            "registry_target",
            "package_name_ownership",
            "version_policy",
            "changelog_policy",
            "registry_consumer_smoke",
        ]:
            value = item.get(key)
            if not isinstance(value, str) or not value.strip() or value.strip().lower() == "pending":
                errors.append(f"{language}.{key} must be filled and not pending")


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
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate S017-007 SDK release approval evidence JSON.")
    parser.add_argument("evidence", help="Path to SDK release approval evidence JSON.")
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

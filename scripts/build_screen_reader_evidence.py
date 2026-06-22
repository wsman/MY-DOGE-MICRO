from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_screen_reader_evidence import REQUIRED_CHECK_IDS, validate


TEMPLATE = ROOT / "production" / "qa" / "evidence" / "manual" / (
    "research-agent-screen-reader-manual-template-2026-06-22.json"
)
DEFAULT_OUTPUT = ROOT / "production" / "qa" / "evidence" / "manual" / (
    "research-agent-screen-reader-manual-generated.json"
)
VALID_RESULTS = {"passed", "failed"}
VALID_CHECK_STATUSES = {"passed", "failed", "blocked", "not_run"}
REQUIRED_ENVIRONMENT = {
    "platform",
    "browser",
    "browser_version",
    "screen_reader",
    "screen_reader_version",
    "web_url",
}
REQUIRED_REDACTION_FLAGS = {"contains_secrets", "contains_sensitive_documents"}


def build_evidence(
    *,
    observations_path: Path,
    template_path: Path = TEMPLATE,
    created_at: str | None = None,
) -> dict[str, Any]:
    template = json.loads(template_path.read_text(encoding="utf-8"))
    observations = _load_observations(observations_path)
    result = observations.get("result")
    if result not in VALID_RESULTS:
        raise ValueError(f"observation result must be one of {', '.join(sorted(VALID_RESULTS))}")

    payload = dict(template)
    payload["created_at"] = created_at or datetime.now(timezone.utc).isoformat()
    payload["result"] = result
    payload["executed_at"] = _required_string(observations, "executed_at")
    payload["summary"] = _required_string(observations, "summary")
    payload["operator"] = _operator(observations)
    payload["environment"] = _environment(template.get("environment"), observations)
    payload["fixtures"] = _merge_optional_dict(template.get("fixtures"), observations.get("fixtures"))
    payload["checks"] = _merge_checks(template["checks"], observations.get("checks"))
    payload["issues"] = _string_list(observations.get("issues"), "issues")
    payload["attachments"] = _string_list(observations.get("attachments"), "attachments")
    payload["redaction_review"] = _redaction_review(template.get("redaction_review"), observations)
    return payload


def _load_observations(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("screen-reader observation input must be a JSON object")
    return payload


def _operator(observations: dict[str, Any]) -> dict[str, str]:
    operator = observations.get("operator")
    if not isinstance(operator, dict):
        raise ValueError("operator is required")
    return {
        "role": _required_string(operator, "role"),
        "initials": _required_string(operator, "initials"),
    }


def _environment(template_value: Any, observations: dict[str, Any]) -> dict[str, Any]:
    environment = observations.get("environment")
    if not isinstance(environment, dict):
        raise ValueError("environment is required")
    missing = [
        key
        for key in sorted(REQUIRED_ENVIRONMENT)
        if not isinstance(environment.get(key), str) or not environment[key].strip()
    ]
    if missing:
        raise ValueError(f"missing environment fields: {', '.join(missing)}")
    merged = dict(template_value) if isinstance(template_value, dict) else {}
    merged.update(environment)
    return merged


def _merge_optional_dict(template_value: Any, update_value: Any) -> dict[str, Any]:
    merged = dict(template_value) if isinstance(template_value, dict) else {}
    if update_value is None:
        return merged
    if not isinstance(update_value, dict):
        raise ValueError("fixtures must be an object when provided")
    merged.update(update_value)
    return merged


def _merge_checks(template_checks: list[dict[str, Any]], raw_checks: Any) -> list[dict[str, Any]]:
    updates = _check_map(raw_checks)
    missing = REQUIRED_CHECK_IDS - set(updates)
    extra = set(updates) - REQUIRED_CHECK_IDS
    if missing:
        raise ValueError(f"missing checks: {', '.join(sorted(missing))}")
    if extra:
        raise ValueError(f"unexpected checks: {', '.join(sorted(extra))}")

    merged: list[dict[str, Any]] = []
    for template_check in template_checks:
        check_id = template_check["id"]
        item = dict(template_check)
        item.update(updates[check_id])
        item["id"] = check_id
        status = item.get("status")
        if status not in VALID_CHECK_STATUSES:
            raise ValueError(f"{check_id}: status must be one of {', '.join(sorted(VALID_CHECK_STATUSES))}")
        merged.append(item)
    return merged


def _check_map(raw_checks: Any) -> dict[str, dict[str, Any]]:
    if isinstance(raw_checks, list):
        return {
            item.get("id"): item
            for item in raw_checks
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
    if isinstance(raw_checks, dict):
        return {
            check_id: dict(value, id=check_id)
            for check_id, value in raw_checks.items()
            if isinstance(check_id, str) and isinstance(value, dict)
        }
    raise ValueError("checks must be an object keyed by check id or a list")


def _redaction_review(template_value: Any, observations: dict[str, Any]) -> dict[str, Any]:
    update = observations.get("redaction_review")
    if not isinstance(update, dict):
        raise ValueError("redaction_review is required")
    for key in sorted(REQUIRED_REDACTION_FLAGS):
        _required_bool(update, key)
    review = dict(template_value) if isinstance(template_value, dict) else {}
    review.update(update)
    return review


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} is required")
    return value


def _required_bool(payload: dict[str, Any], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"redaction_review.{key} must be an explicit boolean")
    return value


def _string_list(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError(f"{field} must be a list of non-empty strings")
    return value


def write_evidence(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build S017-006 screen-reader manual evidence from compact operator observations."
    )
    parser.add_argument("--observations", required=True, help="Screen-reader observation JSON path.")
    parser.add_argument("--template", default=str(TEMPLATE), help="Screen-reader evidence template path.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Evidence JSON output path.")
    parser.add_argument("--created-at", help="ISO-8601 evidence creation timestamp.")
    args = parser.parse_args(argv)

    try:
        payload = build_evidence(
            observations_path=Path(args.observations),
            template_path=Path(args.template),
            created_at=args.created_at,
        )
        errors = validate(payload)
    except ValueError as exc:
        print(json.dumps({"passed_validation": False, "errors": [str(exc)]}, indent=2, sort_keys=True))
        return 1

    result = {
        "output": str(Path(args.output)),
        "result": payload["result"],
        "passed_validation": not errors,
        "errors": errors,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    if errors:
        return 1
    write_evidence(Path(args.output), payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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

from scripts.validate_sdk_release_approval_evidence import REQUIRED_LANGUAGES, validate


TEMPLATE = ROOT / "production" / "qa" / "evidence" / "sdk" / "sdk-release-approval-template-2026-06-22.json"
DEFAULT_OUTPUT = ROOT / "production" / "qa" / "evidence" / "sdk" / "sdk-release-approval-generated.json"
VALID_RESULTS = {"approved", "needs_revision", "rejected"}


def build_evidence(
    *,
    decisions_path: Path,
    template_path: Path = TEMPLATE,
    created_at: str | None = None,
) -> dict[str, Any]:
    template = json.loads(template_path.read_text(encoding="utf-8"))
    decisions = _load_decision_payload(decisions_path)
    result = decisions.get("result")
    if result not in VALID_RESULTS:
        raise ValueError(f"decision result must be one of {', '.join(sorted(VALID_RESULTS))}")

    payload = dict(template)
    payload["created_at"] = created_at or datetime.now(timezone.utc).isoformat()
    payload["result"] = result
    payload["release_manager"] = _release_manager(decisions)
    payload["approved_at"] = _required_string(decisions, "approved_at")
    payload["issue_refs"] = _string_list(decisions.get("issue_refs"))
    payload["security_review"] = _security_review(decisions)
    payload["packages"] = _merge_packages(template["packages"], _package_map(decisions))
    payload["blockers"] = [] if result == "approved" else _non_approved_blockers(result, payload["issue_refs"])
    return payload


def _load_decision_payload(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("SDK release decision input must be a JSON object")
    return payload


def _release_manager(decisions: dict[str, Any]) -> dict[str, str]:
    manager = decisions.get("release_manager")
    if not isinstance(manager, dict):
        raise ValueError("release_manager is required")
    return {
        "role": _required_string(manager, "role"),
        "initials": _required_string(manager, "initials"),
    }


def _security_review(decisions: dict[str, Any]) -> dict[str, bool]:
    review = decisions.get("security_review", {})
    if not isinstance(review, dict):
        raise ValueError("security_review must be an object when provided")
    return {
        "no_credentials_in_package_config": bool(review.get("no_credentials_in_package_config", False)),
        "typescript_sources_excluded_from_tarball": bool(review.get("typescript_sources_excluded_from_tarball", False)),
        "redaction_behavior_documented": bool(review.get("redaction_behavior_documented", False)),
        "contains_credentials": bool(review.get("contains_credentials", False)),
    }


def _package_map(decisions: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = decisions.get("packages")
    if isinstance(raw, list):
        by_language = {
            item.get("language"): item
            for item in raw
            if isinstance(item, dict) and isinstance(item.get("language"), str)
        }
    elif isinstance(raw, dict):
        by_language = {
            language: dict(value, language=language)
            for language, value in raw.items()
            if isinstance(value, dict)
        }
    else:
        raise ValueError("packages must be an object keyed by language or a list")
    missing = REQUIRED_LANGUAGES - set(by_language)
    extra = set(by_language) - REQUIRED_LANGUAGES
    if missing:
        raise ValueError(f"missing packages: {', '.join(sorted(missing))}")
    if extra:
        raise ValueError(f"unexpected packages: {', '.join(sorted(extra))}")
    return by_language


def _merge_packages(template_packages: list[dict[str, Any]], updates: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    merged = []
    for template_package in template_packages:
        language = template_package["language"]
        item = dict(template_package)
        item.update(updates[language])
        item["language"] = language
        merged.append(item)
    return merged


def _non_approved_blockers(result: str, issue_refs: list[str]) -> list[str]:
    if issue_refs:
        return [f"SDK release approval result is {result}; see issue_refs"]
    return [f"SDK release approval result is {result}; issue_refs required before closure"]


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} is required")
    return value


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError("issue_refs must be a list of non-empty strings")
    return value


def write_evidence(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build S017-007 SDK release approval evidence from release-manager decisions.")
    parser.add_argument("--decisions", required=True, help="Release-manager decision JSON path.")
    parser.add_argument("--template", default=str(TEMPLATE), help="Release approval evidence template path.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Evidence JSON output path.")
    parser.add_argument("--created-at", help="ISO-8601 evidence creation timestamp.")
    args = parser.parse_args(argv)

    try:
        payload = build_evidence(
            decisions_path=Path(args.decisions),
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

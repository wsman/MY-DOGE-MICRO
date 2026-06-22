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

from scripts.validate_financial_provider_approval_evidence import REQUIRED_CAPABILITIES, validate


TEMPLATE = ROOT / "production" / "qa" / "evidence" / "provider" / "financial-provider-approval-template-2026-06-22.json"
DEFAULT_OUTPUT = ROOT / "production" / "qa" / "evidence" / "provider" / "financial-provider-approval-generated.json"
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
    payload["operator"] = _operator(decisions)
    payload["approved_at"] = _required_string(decisions, "approved_at")
    payload["issue_refs"] = _string_list(decisions.get("issue_refs"))
    payload["redaction_review"] = _redaction_review(decisions, result)
    payload["decisions"] = _merge_decisions(template["decisions"], _decision_map(decisions))
    payload["blockers"] = [] if result == "approved" else _non_approved_blockers(result, payload["issue_refs"])
    return payload


def _load_decision_payload(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("provider decision input must be a JSON object")
    return payload


def _operator(decisions: dict[str, Any]) -> dict[str, str]:
    operator = decisions.get("operator")
    if not isinstance(operator, dict):
        raise ValueError("operator is required")
    return {
        "role": _required_string(operator, "role"),
        "initials": _required_string(operator, "initials"),
    }


def _redaction_review(decisions: dict[str, Any], result: str) -> dict[str, bool]:
    review = decisions.get("redaction_review")
    if not isinstance(review, dict):
        raise ValueError("redaction_review is required")
    return {
        "contains_credentials": _required_bool(review, "contains_credentials"),
        "contains_proprietary_data": _required_bool(review, "contains_proprietary_data"),
        "repository_storage_approved": _required_bool(review, "repository_storage_approved"),
    }


def _decision_map(decisions: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = decisions.get("decisions")
    if isinstance(raw, list):
        by_capability = {
            item.get("capability"): item
            for item in raw
            if isinstance(item, dict) and isinstance(item.get("capability"), str)
        }
    elif isinstance(raw, dict):
        by_capability = {
            capability: dict(value, capability=capability)
            for capability, value in raw.items()
            if isinstance(value, dict)
        }
    else:
        raise ValueError("decisions must be an object keyed by capability or a list")
    missing = REQUIRED_CAPABILITIES - set(by_capability)
    extra = set(by_capability) - REQUIRED_CAPABILITIES
    if missing:
        raise ValueError(f"missing decisions: {', '.join(sorted(missing))}")
    if extra:
        raise ValueError(f"unexpected decisions: {', '.join(sorted(extra))}")
    return by_capability


def _merge_decisions(template_decisions: list[dict[str, Any]], updates: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    merged = []
    for template_decision in template_decisions:
        capability = template_decision["capability"]
        item = dict(template_decision)
        item.update(updates[capability])
        item["capability"] = capability
        merged.append(item)
    return merged


def _non_approved_blockers(result: str, issue_refs: list[str]) -> list[str]:
    if issue_refs:
        return [f"provider approval result is {result}; see issue_refs"]
    return [f"provider approval result is {result}; issue_refs required before closure"]


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
    parser = argparse.ArgumentParser(description="Build S017-003 financial provider approval evidence from operator decisions.")
    parser.add_argument("--decisions", required=True, help="Operator decision JSON path.")
    parser.add_argument("--template", default=str(TEMPLATE), help="Approval evidence template path.")
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

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

SCHEMA = "doge.financial_provider_approval.v1"
STORY_ID = "S017-003"
REQUIRED_CAPABILITIES = {
    "financial_statements",
    "announcements",
    "consensus",
    "industry_classification",
    "risk_factors",
}
REQUIRED_CASE_TYPES = {"ok", "stale_data", "provider_unavailable", "entitlement_denied", "malformed"}
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
        errors.append("not_run evidence is an approval template/preflight artifact, not completed provider approval")
    if result in {"approved", "needs_revision", "rejected"}:
        errors.extend(placeholder_errors(payload))
        errors.extend(secret_leak_errors(payload))

    contract = _dict(payload.get("contract"))
    contract_errors = _validate_contract_paths(contract)
    errors.extend(contract_errors)

    decisions = payload.get("decisions")
    if not isinstance(decisions, list):
        errors.append("decisions must be a list")
        decisions = []
    decision_map = {
        item.get("capability"): item
        for item in decisions
        if isinstance(item, dict) and isinstance(item.get("capability"), str)
    }
    missing = REQUIRED_CAPABILITIES - set(decision_map)
    extra = set(decision_map) - REQUIRED_CAPABILITIES
    if missing:
        errors.append(f"missing decisions: {', '.join(sorted(missing))}")
    if extra:
        errors.append(f"unexpected decisions: {', '.join(sorted(extra))}")

    for item in decisions:
        if not isinstance(item, dict):
            errors.append("each decision must be an object")
            continue
        _validate_decision(item, result, errors)

    operator = _dict(payload.get("operator"))
    if result in {"approved", "needs_revision", "rejected"}:
        _require_non_empty(operator.get("role"), "operator.role", errors)
        _require_non_empty(operator.get("initials"), "operator.initials", errors)
        _require_timestamp(payload.get("approved_at"), "approved_at", errors)

    if result == "approved":
        for capability, item in decision_map.items():
            if item.get("decision_status") != "approved":
                errors.append(f"{capability}: approved evidence requires decision_status=approved")
        redaction = _dict(payload.get("redaction_review"))
        if redaction.get("repository_storage_approved") is not True:
            errors.append("approved evidence requires redaction_review.repository_storage_approved=true")

    if result in {"needs_revision", "rejected"}:
        if not payload.get("issue_refs"):
            errors.append(f"{result} evidence requires issue_refs")

    redaction = _dict(payload.get("redaction_review"))
    if redaction.get("contains_credentials") is True:
        errors.append("redaction_review.contains_credentials must be false")
    if redaction.get("contains_proprietary_data") is True and result == "approved":
        errors.append("approved evidence must not contain proprietary data")
    if _contains_secret(payload):
        errors.append("evidence appears to contain a bearer token, provider key, or credential")

    return errors


def _validate_decision(item: dict[str, Any], result: Any, errors: list[str]) -> None:
    capability = item.get("capability")
    status = item.get("decision_status")
    if status not in DECISION_STATUSES:
        errors.append(f"{capability}: decision_status must be one of {', '.join(sorted(DECISION_STATUSES))}")
    for key in ["preferred_provider_direction", "local_fallback"]:
        _require_non_empty(item.get(key), f"{capability}.{key}", errors)

    if result == "approved":
        for key in [
            "approved_provider",
            "license_scope",
            "fixture_storage_policy",
            "freshness_requirement",
            "provenance_requirement",
        ]:
            value = item.get(key)
            if not isinstance(value, str) or not value.strip() or value.strip().lower() == "pending":
                errors.append(f"{capability}.{key} must be filled and not pending")


def _validate_contract_paths(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    fixture_contract = contract.get("fixture_contract")
    synthetic_samples = contract.get("synthetic_samples")
    if not isinstance(fixture_contract, str) or not fixture_contract.strip():
        errors.append("contract.fixture_contract is required")
    if not isinstance(synthetic_samples, str) or not synthetic_samples.strip():
        errors.append("contract.synthetic_samples is required")
    if errors:
        return errors

    contract_path = ROOT / fixture_contract
    samples_path = ROOT / synthetic_samples
    if not contract_path.exists():
        errors.append(f"fixture contract not found: {fixture_contract}")
        return errors
    if not samples_path.exists():
        errors.append(f"synthetic samples not found: {synthetic_samples}")
        return errors

    contract_payload = json.loads(contract_path.read_text(encoding="utf-8"))
    samples_payload = json.loads(samples_path.read_text(encoding="utf-8"))
    if contract_payload.get("status") != contract.get("contract_status"):
        errors.append("contract.contract_status does not match fixture contract status")
    if samples_payload.get("status") != contract.get("synthetic_samples_status"):
        errors.append("contract.synthetic_samples_status does not match samples status")

    connectors = _dict(contract_payload.get("connectors"))
    samples = _dict(samples_payload.get("connectors"))
    if set(connectors) != REQUIRED_CAPABILITIES:
        errors.append("fixture contract connectors do not match required capabilities")
    if set(samples) != REQUIRED_CAPABILITIES:
        errors.append("synthetic sample connectors do not match required capabilities")

    allowed_statuses = set(contract_payload.get("allowed_provider_statuses", []))
    for capability, spec in connectors.items():
        required_fields = spec.get("required_fields", [])
        connector_samples = _dict(samples.get(capability)).get("samples", [])
        if not isinstance(connector_samples, list):
            errors.append(f"{capability}: samples must be a list")
            continue
        by_case_type = {
            item.get("case_type"): item
            for item in connector_samples
            if isinstance(item, dict) and isinstance(item.get("case_type"), str)
        }
        if set(by_case_type) != REQUIRED_CASE_TYPES:
            errors.append(f"{capability}: samples must cover {', '.join(sorted(REQUIRED_CASE_TYPES))}")
        for case_type, sample in by_case_type.items():
            if case_type == "malformed":
                payload = _dict(sample.get("payload"))
                if not any(field not in payload for field in required_fields):
                    errors.append(f"{capability}: malformed sample must omit at least one required field")
                continue
            missing = [field for field in required_fields if field not in sample]
            if missing:
                errors.append(f"{capability} {case_type}: missing required fields {missing}")
            if sample.get("license_scope") != "test_synthetic":
                errors.append(f"{capability} {case_type}: license_scope must be test_synthetic")
            if sample.get("provider_status") not in allowed_statuses:
                errors.append(f"{capability} {case_type}: provider_status is not allowed")
            if sample.get("provider_status") != case_type:
                errors.append(f"{capability} {case_type}: provider_status must match case_type")
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
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate S017-003 financial provider approval evidence JSON.")
    parser.add_argument("evidence", help="Path to financial provider approval evidence JSON.")
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

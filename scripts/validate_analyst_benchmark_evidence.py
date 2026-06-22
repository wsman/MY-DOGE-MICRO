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

from scripts.analyst_trend_history import validate_trend_history_jsonl
from scripts.evidence_placeholders import placeholder_errors
from scripts.evidence_redaction import secret_leak_errors

SCHEMA = "doge.analyst_labeled_eval_benchmark.v1"
STORY_ID = "W3-live"
MATERIAL_CASE_KEYS = {
    "annual_report_cases",
    "presentation_cases",
    "chart_image_cases",
    "portfolio_csv_cases",
    "unsupported_claim_cases",
    "multi_turn_cases",
}
THRESHOLD_KEYS = {
    "retrieval_recall_min",
    "retrieval_precision_min",
    "citation_precision_min",
    "numerical_consistency_min",
    "usage_cost_record_coverage_min",
    "latency_p95_ms_max",
    "cost_usd_p95_max",
}
METRIC_KEYS = {
    "retrieval_recall",
    "retrieval_precision",
    "citation_precision",
    "numerical_consistency",
    "usage_cost_record_coverage",
    "latency_p95_ms",
    "cost_usd_p95",
}
SECRET_PATTERNS = [
    re.compile(r"Bearer\s+(?=[A-Za-z0-9._~+/=-]*[._~+/=-])[A-Za-z0-9._~+/=-]{8,}", re.I),
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
    if result not in {"passed", "failed", "not_run"}:
        errors.append("result must be passed, failed, or not_run")
    if result == "not_run" and not allow_template:
        errors.append("not_run evidence is an analyst benchmark template/preflight artifact")
    if result in {"passed", "failed"}:
        errors.extend(placeholder_errors(payload))
        errors.extend(secret_leak_errors(payload))

    errors.extend(_validate_seed_evidence(_dict(payload.get("seed_evidence"))))
    materials = _dict(payload.get("materials"))
    labels = _dict(payload.get("labels"))
    observations = _dict(payload.get("observations"))
    thresholds = _dict(payload.get("thresholds"))
    results = _dict(payload.get("results"))

    if result in {"passed", "failed"}:
        analyst = _dict(payload.get("analyst_review"))
        _require_non_empty(analyst.get("role"), "analyst_review.role", errors)
        _require_non_empty(analyst.get("initials"), "analyst_review.initials", errors)
        _require_timestamp(analyst.get("reviewed_at"), "analyst_review.reviewed_at", errors)
        _validate_completed_materials(materials, errors)
        _validate_completed_labels(labels, errors)
        _validate_completed_observations(observations, errors)
        _validate_completed_thresholds(thresholds, errors)
        _validate_completed_results(
            thresholds,
            results,
            errors,
            enforce_thresholds=result == "passed",
            expected_case_count=materials.get("total_cases") if isinstance(materials.get("total_cases"), int) else None,
        )

    if result == "failed" and not payload.get("issue_refs"):
        errors.append("failed evidence requires issue_refs")

    redaction = _dict(payload.get("redaction_review"))
    for key in [
        "contains_credentials",
        "contains_raw_proprietary_documents",
        "contains_personal_data",
    ]:
        if redaction.get(key) is True:
            errors.append(f"redaction_review.{key} must be false")
    if redaction.get("run_ids_redacted") is not True:
        errors.append("redaction_review.run_ids_redacted must be true")
    if observations.get("raw_sensitive_documents_recorded") is True:
        errors.append("observations.raw_sensitive_documents_recorded must be false")
    if _contains_secret(payload):
        errors.append("evidence appears to contain a bearer token, provider key, or credential")

    return errors


def _validate_seed_evidence(seed: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ["gold_cases", "gold_eval", "seed_report"]:
        value = seed.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"seed_evidence.{key} is required")
            continue
        path = ROOT / value
        if not path.exists():
            errors.append(f"seed evidence not found: {value}")
    gold_cases_value = seed.get("gold_cases")
    if isinstance(gold_cases_value, str) and (ROOT / gold_cases_value).exists():
        cases = json.loads((ROOT / gold_cases_value).read_text(encoding="utf-8"))
        if len(cases) < 30:
            errors.append("seed gold_cases must contain at least 30 cases")
    return errors


def _validate_completed_materials(materials: dict[str, Any], errors: list[str]) -> None:
    for key in MATERIAL_CASE_KEYS:
        value = materials.get(key)
        if not isinstance(value, int) or value < 1:
            errors.append(f"materials.{key} must be at least 1")
    total = materials.get("total_cases")
    if not isinstance(total, int) or total < 30:
        errors.append("materials.total_cases must be at least 30")
    counted = sum(materials.get(key, 0) for key in MATERIAL_CASE_KEYS if isinstance(materials.get(key), int))
    if isinstance(total, int) and counted > total:
        errors.append("materials category counts must not exceed total_cases")
    _require_non_empty(materials.get("material_manifest_ref"), "materials.material_manifest_ref", errors)


def _validate_completed_labels(labels: dict[str, Any], errors: list[str]) -> None:
    minimums = {
        "human_citation_labels": 25,
        "human_numerical_labels": 20,
        "insufficient_evidence_labels": 5,
    }
    for key, minimum in minimums.items():
        value = labels.get(key)
        if not isinstance(value, int) or value < minimum:
            errors.append(f"labels.{key} must be at least {minimum}")
    _require_non_empty(labels.get("label_manifest_ref"), "labels.label_manifest_ref", errors)
    _require_non_empty(labels.get("label_policy_ref"), "labels.label_policy_ref", errors)


def _validate_completed_observations(observations: dict[str, Any], errors: list[str]) -> None:
    _require_non_empty(observations.get("live_kimi_observation_ref"), "observations.live_kimi_observation_ref", errors)
    profiles = observations.get("model_profiles")
    if not isinstance(profiles, list) or not {"financial_research", "vision_analysis"} <= set(profiles):
        errors.append("observations.model_profiles must include financial_research and vision_analysis")
    if observations.get("run_ids_redacted") is not True:
        errors.append("observations.run_ids_redacted must be true")


def _validate_completed_thresholds(thresholds: dict[str, Any], errors: list[str]) -> None:
    for key in THRESHOLD_KEYS:
        value = thresholds.get(key)
        if not isinstance(value, (int, float)):
            errors.append(f"thresholds.{key} must be numeric")
    for key in [
        "retrieval_recall_min",
        "retrieval_precision_min",
        "citation_precision_min",
        "numerical_consistency_min",
        "usage_cost_record_coverage_min",
    ]:
        value = thresholds.get(key)
        if isinstance(value, (int, float)) and not 0 <= value <= 1:
            errors.append(f"thresholds.{key} must be between 0 and 1")


def _validate_completed_results(
    thresholds: dict[str, Any],
    results: dict[str, Any],
    errors: list[str],
    *,
    enforce_thresholds: bool,
    expected_case_count: int | None,
) -> None:
    for key in METRIC_KEYS:
        value = results.get(key)
        if not isinstance(value, (int, float)):
            errors.append(f"results.{key} must be numeric")
    for result_key, threshold_key in [
        ("retrieval_recall", "retrieval_recall_min"),
        ("retrieval_precision", "retrieval_precision_min"),
        ("citation_precision", "citation_precision_min"),
        ("numerical_consistency", "numerical_consistency_min"),
        ("usage_cost_record_coverage", "usage_cost_record_coverage_min"),
    ]:
        result_value = results.get(result_key)
        threshold_value = thresholds.get(threshold_key)
        if (
            enforce_thresholds
            and isinstance(result_value, (int, float))
            and isinstance(threshold_value, (int, float))
            and result_value < threshold_value
        ):
            errors.append(f"results.{result_key} is below threshold {threshold_key}")
    for result_key, threshold_key in [
        ("latency_p95_ms", "latency_p95_ms_max"),
        ("cost_usd_p95", "cost_usd_p95_max"),
    ]:
        result_value = results.get(result_key)
        threshold_value = thresholds.get(threshold_key)
        if (
            enforce_thresholds
            and isinstance(result_value, (int, float))
            and isinstance(threshold_value, (int, float))
            and result_value > threshold_value
        ):
            errors.append(f"results.{result_key} exceeds threshold {threshold_key}")
    trend_history_ref = results.get("trend_history_ref")
    _require_non_empty(trend_history_ref, "results.trend_history_ref", errors)
    if isinstance(trend_history_ref, str) and trend_history_ref.strip():
        _validate_local_trend_history_ref(trend_history_ref, expected_case_count=expected_case_count, errors=errors)


def _validate_local_trend_history_ref(
    trend_history_ref: str,
    *,
    expected_case_count: int | None,
    errors: list[str],
) -> None:
    path = _local_ref_path(trend_history_ref)
    if path is None:
        return
    if not path.exists():
        errors.append(f"results.trend_history_ref not found: {trend_history_ref}")
        return
    for error in validate_trend_history_jsonl(path, expected_case_count=expected_case_count):
        errors.append(f"results.trend_history_ref invalid: {error}")


def _local_ref_path(value: str) -> Path | None:
    if "://" in value:
        return None
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


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
    parser = argparse.ArgumentParser(description="Validate W3-live analyst-labeled eval benchmark evidence JSON.")
    parser.add_argument("evidence", help="Path to analyst benchmark evidence JSON.")
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

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any

from scripts.evidence_placeholders import placeholder_errors
from scripts.evidence_redaction import secret_leak_errors


TREND_HISTORY_METRIC_KEYS = {
    "citation_precision",
    "cost_usd_p95",
    "latency_p95_ms",
    "numerical_consistency",
    "retrieval_precision",
    "retrieval_recall",
    "usage_cost_record_coverage",
}


def validate_trend_history_jsonl(
    path: Path,
    *,
    expected_case_count: int | None = None,
    subject: str = "trend history",
) -> list[str]:
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        return ["JSONL draft must contain at least one row"]
    errors: list[str] = []
    template_rows = 0
    for index, line in enumerate(lines, 1):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {index}: invalid JSON: {exc.msg}")
            continue
        if not isinstance(payload, dict):
            errors.append(f"line {index}: trend history row must be an object")
            continue
        if payload.get("status") == "template":
            template_rows += 1
        errors.extend(f"line {index}: {error}" for error in _trend_history_row_errors(payload, expected_case_count))
        errors.extend(f"line {index}: {error}" for error in placeholder_errors(payload, subject=subject))
        errors.extend(f"line {index}: {error}" for error in secret_leak_errors(payload, subject=subject))
    if template_rows == len(lines):
        errors.append("JSONL draft must not contain only template rows")
    return errors


def _trend_history_row_errors(row: dict[str, Any], expected_case_count: int | None) -> list[str]:
    errors: list[str] = []
    status = row.get("status")
    if status not in {"passed", "failed"}:
        errors.append("status must be passed or failed")
    observed_at = row.get("observed_at")
    if not isinstance(observed_at, str) or not observed_at.strip():
        errors.append("observed_at is required")
    else:
        try:
            datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
        except ValueError:
            errors.append("observed_at must be ISO-8601")
    run_hash = row.get("benchmark_run_id_hash")
    if not isinstance(run_hash, str) or not run_hash.startswith("sha256:"):
        errors.append("benchmark_run_id_hash must be a sha256: redacted hash")
    for raw_key in ["run_id", "raw_run_id", "session_id", "raw_session_id"]:
        if raw_key in row:
            errors.append(f"{raw_key} must not be recorded")
    profiles = row.get("profiles")
    if not isinstance(profiles, list) or not {"financial_research", "vision_analysis"} <= set(profiles):
        errors.append("profiles must include financial_research and vision_analysis")
    if expected_case_count is not None and row.get("case_count") != expected_case_count:
        errors.append(f"case_count must match gold case count: {expected_case_count}")
    metrics = row.get("metrics")
    if not isinstance(metrics, dict):
        errors.append("metrics must be an object")
    else:
        for key in sorted(TREND_HISTORY_METRIC_KEYS):
            value = metrics.get(key)
            if not isinstance(value, (int, float)):
                errors.append(f"metrics.{key} must be numeric")
    return errors

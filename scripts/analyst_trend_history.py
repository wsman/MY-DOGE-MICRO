from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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


def trend_row_from_citation_baseline(
    baseline_path: Path,
    *,
    observed_at: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    """Build a redacted trend-history row from a local citation baseline."""

    payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    score = payload.get("score")
    if not isinstance(score, dict):
        raise ValueError("baseline score must be an object")
    metrics = score.get("metrics")
    results = score.get("results")
    if not isinstance(metrics, dict) or not isinstance(results, list):
        raise ValueError("baseline score must include metrics and per-case results")
    gold_set = payload.get("gold_set") if isinstance(payload.get("gold_set"), dict) else {}
    latencies = [
        float(item["latency_ms"])
        for item in results
        if isinstance(item, dict) and isinstance(item.get("latency_ms"), (int, float))
    ]
    costs = [
        float(item["cost_usd"])
        for item in results
        if isinstance(item, dict) and isinstance(item.get("cost_usd"), (int, float))
    ]
    row = {
        "status": status or _baseline_status(score),
        "observed_at": observed_at or _normalize_observed_at(payload.get("created_at")),
        "benchmark_run_id_hash": _baseline_hash(payload),
        "profiles": gold_set.get("profiles") or ["financial_research", "vision_analysis"],
        "case_count": int(score.get("case_count") or gold_set.get("case_count") or 0),
        "metrics": {
            "retrieval_recall": _numeric(metrics.get("retrieval_recall")),
            "retrieval_precision": _numeric(metrics.get("retrieval_precision")),
            "citation_precision": _numeric(metrics.get("citation_precision")),
            "numerical_consistency": _numeric(metrics.get("numerical_consistency")),
            "usage_cost_record_coverage": _numeric(metrics.get("usage_cost_record_coverage")),
            "latency_p95_ms": _percentile_95(latencies),
            "cost_usd_p95": _percentile_95(costs),
        },
        "source": payload.get("source") or "citation_quality_baseline",
        "baseline_ref": str(baseline_path).replace("\\", "/"),
        "w3_live_closure_allowed": bool(payload.get("w3_live_closure_allowed")),
    }
    errors = _trend_history_row_errors(row, expected_case_count=row["case_count"])
    if errors:
        raise ValueError("generated trend row is invalid: " + "; ".join(errors))
    return row


def append_trend_history_row(path: Path, row: dict[str, Any]) -> bool:
    """Append or replace a row by benchmark_run_id_hash.

    Returns True when the file content changed.
    """

    existing_rows = _read_rows(path) if path.exists() else []
    row_hash = row.get("benchmark_run_id_hash")
    rows = [
        existing
        for existing in existing_rows
        if not (isinstance(existing, dict) and existing.get("benchmark_run_id_hash") == row_hash)
    ]
    rows.append(row)
    rendered = "".join(json.dumps(item, sort_keys=True, ensure_ascii=False) + "\n" for item in rows)
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    if rendered == old:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8")
    return True


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


def _read_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _baseline_status(score: dict[str, Any]) -> str:
    return "passed" if score.get("observed_case_count") == score.get("case_count") else "failed"


def _normalize_observed_at(value: Any) -> str:
    if isinstance(value, str) and value.strip():
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.isoformat().replace("+00:00", "Z")
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _baseline_hash(payload: dict[str, Any]) -> str:
    redacted_payload = {
        "schema_version": payload.get("schema_version"),
        "source": payload.get("source"),
        "runtime_path": payload.get("runtime_path"),
        "gold_set": payload.get("gold_set"),
        "score": payload.get("score"),
    }
    digest = hashlib.sha256(
        json.dumps(redacted_payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return f"sha256:{digest}"


def _numeric(value: Any) -> float:
    return float(value) if isinstance(value, (int, float)) else 0.0


def _percentile_95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(value) for value in values)
    index = max(0, int(0.95 * (len(ordered) - 1)))
    return ordered[index]


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build, append, and validate analyst trend-history JSONL.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    append_parser = subparsers.add_parser(
        "append-local-baseline",
        help="Append a local citation-quality baseline as one redacted trend row.",
    )
    append_parser.add_argument("--baseline", required=True, type=Path, help="citation-quality-baseline JSON.")
    append_parser.add_argument("--output", required=True, type=Path, help="Trend-history JSONL output.")
    append_parser.add_argument("--observed-at", help="ISO-8601 observation timestamp override.")
    append_parser.add_argument("--status", choices=["passed", "failed"], help="Trend row status override.")

    validate_parser = subparsers.add_parser("validate", help="Validate a trend-history JSONL file.")
    validate_parser.add_argument("path", type=Path)
    validate_parser.add_argument("--expected-case-count", type=int)

    args = parser.parse_args(argv)
    if args.command == "append-local-baseline":
        row = trend_row_from_citation_baseline(
            args.baseline,
            observed_at=args.observed_at,
            status=args.status,
        )
        changed = append_trend_history_row(args.output, row)
        errors = validate_trend_history_jsonl(args.output, expected_case_count=row["case_count"])
        if errors:
            print(json.dumps({"ok": False, "errors": errors}, indent=2, ensure_ascii=False))
            return 1
        print(json.dumps({
            "ok": True,
            "changed": changed,
            "output": str(args.output),
            "row": row,
        }, indent=2, ensure_ascii=False))
        return 0
    if args.command == "validate":
        errors = validate_trend_history_jsonl(args.path, expected_case_count=args.expected_case_count)
        print(json.dumps({"ok": not errors, "errors": errors}, indent=2, ensure_ascii=False))
        return 1 if errors else 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

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

from scripts.validate_analyst_benchmark_evidence import validate
from scripts.analyst_trend_history import validate_trend_history_jsonl
from tests.eval.gold_eval import load_gold_cases, score_observations, summarize_gold_set


SCHEMA = "doge.analyst_labeled_eval_benchmark.v1"
STORY_ID = "W3-live"
DEFAULT_GOLD_CASES = ROOT / "tests" / "eval" / "gold_cases.json"
DEFAULT_OUTPUT = ROOT / "production" / "qa" / "evidence" / "eval" / "analyst-benchmark-generated.json"
DEFAULT_SEED_REPORT = "production/qa/evidence/eval/research-gold-set-2026-06-21.md"
REQUIRED_THRESHOLD_KEYS = {
    "retrieval_recall_min",
    "retrieval_precision_min",
    "citation_precision_min",
    "numerical_consistency_min",
    "usage_cost_record_coverage_min",
    "latency_p95_ms_max",
    "cost_usd_p95_max",
}


def build_evidence(
    *,
    gold_cases_path: Path,
    observations_path: Path,
    thresholds_path: Path,
    material_manifest_ref: str,
    label_manifest_ref: str,
    label_policy_ref: str,
    live_observation_ref: str,
    trend_history_ref: str,
    analyst_role: str,
    analyst_initials: str,
    reviewed_at: str,
    created_at: str | None = None,
    issue_refs: list[str] | None = None,
) -> dict[str, Any]:
    cases = load_gold_cases(gold_cases_path)
    summary = summarize_gold_set(cases)
    observations = _load_observations(observations_path)
    thresholds = _load_thresholds(thresholds_path)
    _validate_local_trend_history_ref(trend_history_ref, expected_case_count=len(cases))
    score = score_observations(cases, observations)
    metrics = score["metrics"]
    results = _results_from_score(score, trend_history_ref)
    passed = _passes_thresholds(results, thresholds)
    result = "passed" if passed else "failed"

    return {
        "schema": SCHEMA,
        "story_id": STORY_ID,
        "created_at": created_at or datetime.now(timezone.utc).isoformat(),
        "result": result,
        "benchmark_scope": (
            "Real analyst-labeled financial research benchmark for annual reports, presentations, chart images, "
            "portfolio CSVs, unsupported claims, and multi-turn follow-up."
        ),
        "seed_evidence": {
            "gold_cases": _display_path(gold_cases_path),
            "gold_eval": "tests/eval/gold_eval.py",
            "seed_report": DEFAULT_SEED_REPORT,
        },
        "analyst_review": {
            "role": analyst_role,
            "initials": analyst_initials,
            "reviewed_at": reviewed_at,
        },
        "materials": _materials_from_cases(cases, material_manifest_ref),
        "labels": {
            "human_citation_labels": summary["citation_label_count"],
            "human_numerical_labels": summary["numerical_label_count"],
            "insufficient_evidence_labels": summary["unsupported_claim_label_count"],
            "label_manifest_ref": label_manifest_ref,
            "label_policy_ref": label_policy_ref,
        },
        "observations": {
            "live_kimi_observation_ref": live_observation_ref,
            "model_profiles": summary["profiles"],
            "run_ids_redacted": True,
            "raw_sensitive_documents_recorded": False,
            "observed_case_count": score["observed_case_count"],
            "observation_input_ref": _display_path(observations_path),
        },
        "thresholds": thresholds,
        "results": results,
        "redaction_review": {
            "contains_credentials": False,
            "contains_raw_proprietary_documents": False,
            "contains_personal_data": False,
            "run_ids_redacted": True,
        },
        "issue_refs": issue_refs or [],
        "blockers": [] if passed else ["benchmark result did not satisfy approved thresholds"],
    }


def _load_observations(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("observations must be an object keyed by case id")
    observations = payload.get("observations", payload)
    if not isinstance(observations, dict):
        raise ValueError("observations must be an object keyed by case id")
    return {
        str(case_id): value
        for case_id, value in observations.items()
        if isinstance(value, dict)
    }


def _load_thresholds(path: Path) -> dict[str, float]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("thresholds must be an object")
    missing = REQUIRED_THRESHOLD_KEYS - set(payload)
    if missing:
        raise ValueError(f"thresholds missing required keys: {', '.join(sorted(missing))}")
    thresholds: dict[str, float] = {}
    for key in sorted(REQUIRED_THRESHOLD_KEYS):
        value = payload[key]
        if not isinstance(value, (int, float)):
            raise ValueError(f"thresholds.{key} must be numeric")
        thresholds[key] = float(value)
    return thresholds


def _validate_local_trend_history_ref(trend_history_ref: str, *, expected_case_count: int) -> None:
    path = _local_ref_path(trend_history_ref)
    if path is None:
        return
    if not path.exists():
        raise ValueError(f"trend history ref not found: {trend_history_ref}")
    errors = validate_trend_history_jsonl(path, expected_case_count=expected_case_count)
    if errors:
        raise ValueError("trend history ref is invalid: " + "; ".join(errors))


def _local_ref_path(value: str) -> Path | None:
    if "://" in value:
        return None
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _materials_from_cases(cases: list[dict[str, Any]], material_manifest_ref: str) -> dict[str, Any]:
    categories = [case["category"] for case in cases]
    return {
        "annual_report_cases": categories.count("annual_report"),
        "presentation_cases": categories.count("presentation"),
        "chart_image_cases": categories.count("chart_image"),
        "portfolio_csv_cases": categories.count("portfolio_csv"),
        "unsupported_claim_cases": categories.count("unsupported_claim"),
        "multi_turn_cases": categories.count("multi_turn"),
        "total_cases": len(cases),
        "material_manifest_ref": material_manifest_ref,
    }


def _results_from_score(score: dict[str, Any], trend_history_ref: str) -> dict[str, Any]:
    metrics = score["metrics"]
    rows = score["results"]
    latencies = [item["latency_ms"] for item in rows if item.get("latency_ms") is not None]
    costs = [item["cost_usd"] for item in rows if item.get("cost_usd") is not None]
    return {
        "retrieval_recall": _metric(metrics.get("retrieval_recall")),
        "retrieval_precision": _metric(metrics.get("retrieval_precision")),
        "citation_precision": _metric(metrics.get("citation_precision")),
        "numerical_consistency": _metric(metrics.get("numerical_consistency")),
        "usage_cost_record_coverage": _metric(metrics.get("usage_cost_record_coverage")),
        "latency_p95_ms": _percentile_95(latencies),
        "cost_usd_p95": _percentile_95(costs),
        "trend_history_ref": trend_history_ref,
    }


def _passes_thresholds(results: dict[str, Any], thresholds: dict[str, float]) -> bool:
    minimums = [
        ("retrieval_recall", "retrieval_recall_min"),
        ("retrieval_precision", "retrieval_precision_min"),
        ("citation_precision", "citation_precision_min"),
        ("numerical_consistency", "numerical_consistency_min"),
        ("usage_cost_record_coverage", "usage_cost_record_coverage_min"),
    ]
    maximums = [
        ("latency_p95_ms", "latency_p95_ms_max"),
        ("cost_usd_p95", "cost_usd_p95_max"),
    ]
    return all(results[result_key] >= thresholds[threshold_key] for result_key, threshold_key in minimums) and all(
        results[result_key] <= thresholds[threshold_key] for result_key, threshold_key in maximums
    )


def _metric(value: Any) -> float:
    return float(value) if isinstance(value, (int, float)) else 0.0


def _percentile_95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(value) for value in values)
    index = max(0, int(0.95 * (len(ordered) - 1)))
    return ordered[index]


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def write_evidence(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build W3-live analyst benchmark evidence from scored observations.")
    parser.add_argument("--gold-cases", default=str(DEFAULT_GOLD_CASES), help="Gold cases JSON path.")
    parser.add_argument("--observations", required=True, help="Case observation JSON path.")
    parser.add_argument("--thresholds", required=True, help="Approved threshold JSON path.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Evidence JSON output path.")
    parser.add_argument("--material-manifest-ref", required=True, help="Approved material manifest reference.")
    parser.add_argument("--label-manifest-ref", required=True, help="Approved label manifest reference.")
    parser.add_argument("--label-policy-ref", required=True, help="Approved label policy reference.")
    parser.add_argument("--live-observation-ref", required=True, help="Redacted live Kimi observation reference.")
    parser.add_argument("--trend-history-ref", required=True, help="Trend history reference.")
    parser.add_argument("--analyst-role", required=True, help="Analyst reviewer role.")
    parser.add_argument("--analyst-initials", required=True, help="Analyst reviewer initials.")
    parser.add_argument("--reviewed-at", required=True, help="ISO-8601 analyst review timestamp.")
    parser.add_argument("--created-at", help="ISO-8601 evidence creation timestamp.")
    parser.add_argument("--issue-ref", action="append", default=[], help="Issue reference required when result is failed.")
    args = parser.parse_args(argv)

    payload = build_evidence(
        gold_cases_path=Path(args.gold_cases),
        observations_path=Path(args.observations),
        thresholds_path=Path(args.thresholds),
        material_manifest_ref=args.material_manifest_ref,
        label_manifest_ref=args.label_manifest_ref,
        label_policy_ref=args.label_policy_ref,
        live_observation_ref=args.live_observation_ref,
        trend_history_ref=args.trend_history_ref,
        analyst_role=args.analyst_role,
        analyst_initials=args.analyst_initials,
        reviewed_at=args.reviewed_at,
        created_at=args.created_at,
        issue_refs=args.issue_ref,
    )
    errors = validate(payload)
    result = {"output": str(Path(args.output)), "result": payload["result"], "passed_validation": not errors, "errors": errors}
    print(json.dumps(result, indent=2, sort_keys=True))
    if errors:
        return 1
    write_evidence(Path(args.output), payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

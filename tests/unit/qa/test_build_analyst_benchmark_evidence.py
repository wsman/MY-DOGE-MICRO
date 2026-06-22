import json
from pathlib import Path
import subprocess
import sys

from scripts.build_analyst_benchmark_evidence import build_evidence
from scripts.validate_analyst_benchmark_evidence import validate


ROOT = Path(__file__).resolve().parents[3]
GOLD_CASES = ROOT / "tests" / "eval" / "gold_cases.json"


def test_build_passed_analyst_benchmark_evidence(tmp_path):
    observations = tmp_path / "observations.json"
    thresholds = tmp_path / "thresholds.json"
    _write_perfect_observations(observations)
    _write_thresholds(thresholds)

    payload = build_evidence(
        gold_cases_path=GOLD_CASES,
        observations_path=observations,
        thresholds_path=thresholds,
        material_manifest_ref="production/qa/evidence/eval/material-manifest-approved.json",
        label_manifest_ref="production/qa/evidence/eval/label-manifest-approved.json",
        label_policy_ref="docs/progress/financial-eval-gold-set.md",
        live_observation_ref="production/qa/evidence/eval/live-kimi-observations-redacted.json",
        trend_history_ref="production/qa/evidence/eval/trend-history.jsonl",
        analyst_role="research-qa-analyst",
        analyst_initials="QA",
        reviewed_at="2026-06-22T01:00:00Z",
        created_at="2026-06-22T01:01:00Z",
    )

    assert payload["result"] == "passed"
    assert payload["materials"]["total_cases"] >= 30
    assert payload["labels"]["human_citation_labels"] >= 25
    assert payload["labels"]["human_numerical_labels"] >= 20
    assert payload["labels"]["insufficient_evidence_labels"] >= 5
    assert payload["observations"]["observed_case_count"] == payload["materials"]["total_cases"]
    assert payload["results"]["citation_precision"] == 1.0
    assert payload["results"]["numerical_consistency"] == 1.0
    assert validate(payload) == []


def test_build_failed_analyst_benchmark_evidence_validates_with_issue_ref(tmp_path):
    observations = tmp_path / "observations.json"
    thresholds = tmp_path / "thresholds.json"
    _write_perfect_observations(observations)
    _write_thresholds(thresholds, latency_p95_ms_max=1.0)

    payload = build_evidence(
        gold_cases_path=GOLD_CASES,
        observations_path=observations,
        thresholds_path=thresholds,
        material_manifest_ref="production/qa/evidence/eval/material-manifest-approved.json",
        label_manifest_ref="production/qa/evidence/eval/label-manifest-approved.json",
        label_policy_ref="docs/progress/financial-eval-gold-set.md",
        live_observation_ref="production/qa/evidence/eval/live-kimi-observations-redacted.json",
        trend_history_ref="production/qa/evidence/eval/trend-history.jsonl",
        analyst_role="research-qa-analyst",
        analyst_initials="QA",
        reviewed_at="2026-06-22T01:00:00Z",
        created_at="2026-06-22T01:01:00Z",
        issue_refs=["BUG-W3-LATENCY-001"],
    )

    assert payload["result"] == "failed"
    assert payload["blockers"] == ["benchmark result did not satisfy approved thresholds"]
    assert validate(payload) == []


def test_build_analyst_benchmark_evidence_cli_writes_valid_output(tmp_path):
    observations = tmp_path / "observations.json"
    thresholds = tmp_path / "thresholds.json"
    output = tmp_path / "analyst-benchmark-2026-06-22.json"
    _write_perfect_observations(observations)
    _write_thresholds(thresholds)
    script = ROOT / "scripts" / "build_analyst_benchmark_evidence.py"

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--observations",
            str(observations),
            "--thresholds",
            str(thresholds),
            "--output",
            str(output),
            "--material-manifest-ref",
            "production/qa/evidence/eval/material-manifest-approved.json",
            "--label-manifest-ref",
            "production/qa/evidence/eval/label-manifest-approved.json",
            "--label-policy-ref",
            "docs/progress/financial-eval-gold-set.md",
            "--live-observation-ref",
            "production/qa/evidence/eval/live-kimi-observations-redacted.json",
            "--trend-history-ref",
            "production/qa/evidence/eval/trend-history.jsonl",
            "--analyst-role",
            "research-qa-analyst",
            "--analyst-initials",
            "QA",
            "--reviewed-at",
            "2026-06-22T01:00:00Z",
            "--created-at",
            "2026-06-22T01:01:00Z",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    cli_result = json.loads(result.stdout)
    assert cli_result["result"] == "passed"
    assert cli_result["passed_validation"] is True
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert validate(payload) == []


def _write_perfect_observations(path: Path) -> None:
    cases = json.loads(GOLD_CASES.read_text(encoding="utf-8"))
    observations = {}
    for case in cases:
        evidence_ids = [item["evidence_id"] for item in case.get("expected_citations", [])]
        numbers = {item["metric"]: item["value"] for item in case.get("expected_numbers", [])}
        observations[case["id"]] = {
            "retrieved_evidence_ids": evidence_ids,
            "cited_evidence_ids": evidence_ids,
            "numbers": numbers,
            "usage": {"cost_usd": 0.01, "latency_ms": 1000},
        }
    path.write_text(json.dumps({"observations": observations}, indent=2, sort_keys=True), encoding="utf-8")


def _write_thresholds(
    path: Path,
    *,
    retrieval_recall_min: float = 1.0,
    retrieval_precision_min: float = 1.0,
    citation_precision_min: float = 1.0,
    numerical_consistency_min: float = 1.0,
    usage_cost_record_coverage_min: float = 1.0,
    latency_p95_ms_max: float = 1000.0,
    cost_usd_p95_max: float = 0.01,
) -> None:
    path.write_text(
        json.dumps(
            {
                "retrieval_recall_min": retrieval_recall_min,
                "retrieval_precision_min": retrieval_precision_min,
                "citation_precision_min": citation_precision_min,
                "numerical_consistency_min": numerical_consistency_min,
                "usage_cost_record_coverage_min": usage_cost_record_coverage_min,
                "latency_p95_ms_max": latency_p95_ms_max,
                "cost_usd_p95_max": cost_usd_p95_max,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

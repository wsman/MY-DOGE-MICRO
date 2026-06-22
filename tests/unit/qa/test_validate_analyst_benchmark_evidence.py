import copy
import json
from pathlib import Path
import subprocess
import sys

from scripts.validate_analyst_benchmark_evidence import validate


ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_PATH = ROOT / "production" / "qa" / "evidence" / "eval" / (
    "analyst-benchmark-template-2026-06-22.json"
)


def _template() -> dict:
    return json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))


def _passed() -> dict:
    payload = copy.deepcopy(_template())
    payload["result"] = "passed"
    payload["blockers"] = []
    payload["analyst_review"] = {
        "role": "research-qa-analyst",
        "initials": "RA",
        "reviewed_at": "2026-06-22T09:00:00Z",
    }
    payload["materials"].update(
        {
            "annual_report_cases": 8,
            "presentation_cases": 6,
            "chart_image_cases": 5,
            "portfolio_csv_cases": 5,
            "unsupported_claim_cases": 5,
            "multi_turn_cases": 6,
            "total_cases": 35,
            "material_manifest_ref": "operator-secure-store://eval/material-manifest",
        }
    )
    payload["labels"].update(
        {
            "human_citation_labels": 30,
            "human_numerical_labels": 25,
            "insufficient_evidence_labels": 6,
            "label_manifest_ref": "operator-secure-store://eval/labels",
            "label_policy_ref": "operator-secure-store://eval/label-policy",
        }
    )
    payload["observations"].update(
        {
            "live_kimi_observation_ref": "operator-secure-store://eval/live-observations",
            "model_profiles": ["financial_research", "vision_analysis"],
            "run_ids_redacted": True,
            "raw_sensitive_documents_recorded": False,
        }
    )
    payload["thresholds"].update(
        {
            "retrieval_recall_min": 0.85,
            "retrieval_precision_min": 0.75,
            "citation_precision_min": 0.9,
            "numerical_consistency_min": 0.95,
            "usage_cost_record_coverage_min": 0.95,
            "latency_p95_ms_max": 15000,
            "cost_usd_p95_max": 1.25,
        }
    )
    payload["results"].update(
        {
            "retrieval_recall": 0.9,
            "retrieval_precision": 0.8,
            "citation_precision": 0.94,
            "numerical_consistency": 0.98,
            "usage_cost_record_coverage": 1.0,
            "latency_p95_ms": 12000,
            "cost_usd_p95": 0.9,
            "trend_history_ref": "operator-secure-store://eval/trend-history",
        }
    )
    return payload


def test_template_requires_explicit_allow_template():
    payload = _template()

    assert validate(payload, allow_template=True) == []
    errors = validate(payload)

    assert any("not_run evidence" in error for error in errors)


def test_passed_analyst_benchmark_evidence_validates():
    assert validate(_passed()) == []


def test_passed_benchmark_requires_material_category_coverage():
    payload = _passed()
    payload["materials"]["chart_image_cases"] = 0

    errors = validate(payload)

    assert any("chart_image_cases" in error for error in errors)


def test_passed_benchmark_rejects_metric_below_threshold():
    payload = _passed()
    payload["results"]["citation_precision"] = 0.5

    errors = validate(payload)

    assert any("below threshold" in error for error in errors)


def test_failed_benchmark_allows_threshold_miss_with_issue_ref():
    payload = _passed()
    payload["result"] = "failed"
    payload["results"]["citation_precision"] = 0.5
    payload["issue_refs"] = ["BUG-W3-CITATION-001"]

    assert validate(payload) == []


def test_failed_benchmark_requires_issue_ref():
    payload = _passed()
    payload["result"] = "failed"
    payload["results"]["citation_precision"] = 0.5
    payload["issue_refs"] = []

    errors = validate(payload)

    assert any("failed evidence requires issue_refs" in error for error in errors)


def test_passed_benchmark_requires_live_observation_ref():
    payload = _passed()
    payload["observations"]["live_kimi_observation_ref"] = ""

    errors = validate(payload)

    assert any("live_kimi_observation_ref" in error for error in errors)


def test_secret_like_values_are_rejected():
    payload = _passed()
    payload["results"]["trend_history_ref"] = "debug token: should-not-appear"

    errors = validate(payload)

    assert any("appears to contain" in error for error in errors)


def test_cli_allows_template_only_with_flag():
    script = ROOT / "scripts" / "validate_analyst_benchmark_evidence.py"
    denied = subprocess.run(
        [sys.executable, str(script), str(TEMPLATE_PATH)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    allowed = subprocess.run(
        [sys.executable, str(script), str(TEMPLATE_PATH), "--allow-template"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert denied.returncode == 1
    assert "not_run evidence" in denied.stdout
    assert allowed.returncode == 0
    assert json.loads(allowed.stdout)["passed"] is True

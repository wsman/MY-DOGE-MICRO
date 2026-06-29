from __future__ import annotations

import json

from scripts.analyst_trend_history import (
    append_trend_history_row,
    trend_row_from_citation_baseline,
    validate_trend_history_jsonl,
)


def _baseline_payload() -> dict:
    return {
        "schema_version": "doge.citation_quality_baseline.v1",
        "created_at": "2026-06-29T08:00:00+00:00",
        "source": "local_runtime_scripted_gold_set",
        "runtime_path": "PersistedResearchAgentRuntime",
        "w3_live_closure_allowed": False,
        "gold_set": {
            "case_count": 35,
            "profiles": ["financial_research", "vision_analysis"],
        },
        "score": {
            "case_count": 35,
            "observed_case_count": 35,
            "metrics": {
                "retrieval_recall": 1.0,
                "retrieval_precision": 1.0,
                "citation_precision": 1.0,
                "numerical_consistency": 1.0,
                "usage_cost_record_coverage": 1.0,
            },
            "results": [
                {"latency_ms": 5.0, "cost_usd": 0.0},
                {"latency_ms": 10.0, "cost_usd": 0.0},
            ],
        },
    }


def test_trend_row_from_citation_baseline_is_scoreable_and_redacted(tmp_path):
    baseline = tmp_path / "citation-quality-baseline-2026-06-29.json"
    baseline.write_text(json.dumps(_baseline_payload()), encoding="utf-8")

    row = trend_row_from_citation_baseline(
        baseline,
        observed_at="2026-06-29T09:00:00Z",
    )

    assert row["status"] == "passed"
    assert row["benchmark_run_id_hash"].startswith("sha256:")
    assert row["case_count"] == 35
    assert row["profiles"] == ["financial_research", "vision_analysis"]
    assert row["metrics"]["citation_precision"] == 1.0
    assert row["metrics"]["latency_p95_ms"] == 5.0
    assert row["w3_live_closure_allowed"] is False
    assert "run_id" not in row


def test_append_trend_history_row_replaces_same_hash_and_validates(tmp_path):
    baseline = tmp_path / "citation-quality-baseline-2026-06-29.json"
    baseline.write_text(json.dumps(_baseline_payload()), encoding="utf-8")
    row = trend_row_from_citation_baseline(baseline)
    output = tmp_path / "trend-history.jsonl"

    assert append_trend_history_row(output, row) is True
    assert append_trend_history_row(output, row) is False

    lines = output.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert validate_trend_history_jsonl(output, expected_case_count=35) == []

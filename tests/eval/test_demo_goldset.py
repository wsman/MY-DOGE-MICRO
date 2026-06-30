"""Demo gold-set contract tests for reusable eval helpers."""

from __future__ import annotations

from pathlib import Path

from doge.eval.metrics import score_observations
from tests.eval.gold_set_runner import run_all


GOLD_CASES = Path(__file__).with_name("gold_cases.json")


def test_demo_goldset_runs_through_product_eval_metrics(tmp_path) -> None:
    result = run_all(
        gold_cases_path=GOLD_CASES,
        db_path=tmp_path / "runtime.db",
        storage_dir=tmp_path / "storage",
    )

    score = score_observations(result["observations"])

    assert result["w3_live_closure_allowed"] is False
    assert score.case_count == 35
    assert score.observed_case_count == 35
    assert score.metrics["citation_precision"] == 1.0
    assert score.metrics["usage_cost_record_coverage"] == 1.0

from pathlib import Path

from tests.eval.gold_set_runner import run_all


GOLD_CASES = Path(__file__).with_name("gold_cases.json")


def test_runtime_backed_gold_set_produces_complete_observations(tmp_path):
    result = run_all(
        gold_cases_path=GOLD_CASES,
        db_path=tmp_path / "runtime.db",
        storage_dir=tmp_path / "storage",
    )

    score = result["score"]
    observations = result["observations"]

    assert result["w3_live_closure_allowed"] is False
    assert score["case_count"] == 35
    assert score["observed_case_count"] == 35
    assert len(observations) == 35
    assert all(item["status"] == "completed" for item in result["runs"])
    assert all(observation.get("usage") for observation in observations.values())

    required_metrics = {
        "retrieval_recall",
        "retrieval_precision",
        "citation_precision",
        "claim_evidence_precision",
        "support_classification_accuracy",
        "numerical_consistency",
        "usage_cost_record_coverage",
        "avg_cost_usd",
        "avg_latency_ms",
    }
    missing = [
        metric
        for metric in required_metrics
        if score["metrics"].get(metric) is None
    ]
    assert missing == []
    assert score["metrics"]["citation_precision"] == 1.0
    assert all(
        not evidence_id.startswith("evd-evd-")
        for observation in observations.values()
        for evidence_id in observation.get("cited_evidence_ids", [])
    )


def test_runtime_baseline_exposes_w3_live_observation_mapping(tmp_path):
    result = run_all(
        gold_cases_path=GOLD_CASES,
        db_path=tmp_path / "runtime.db",
        storage_dir=tmp_path / "storage",
    )

    w3_input = result["w3_live_observation_input"]

    assert w3_input["schema_version"] == "doge.w3_live_observation_input.v1"
    assert w3_input["w3_live_closure_allowed"] is False
    assert w3_input["observations"] == result["observations"]

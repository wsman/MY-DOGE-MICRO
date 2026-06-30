from pathlib import Path

from tests.eval.rag_retrieval_benchmark import run_benchmark


GOLD_CASES = Path(__file__).with_name("gold_cases.json")


def test_rag_retrieval_benchmark_scores_gold_set_without_live_dependencies(tmp_path):
    result = run_benchmark(
        gold_cases_path=GOLD_CASES,
        db_path=tmp_path / "agent_state.db",
        storage_dir=tmp_path / "storage",
        top_k=5,
    )

    assert result["schema_version"] == "doge.rag_retrieval_benchmark.v1"
    assert result["external_gate_closure_allowed"] is False
    assert result["gold_set"]["case_count"] == 35
    assert result["observed_case_count"] == 35

    metrics = result["metrics"]
    assert metrics["retrieval_recall_at_k"] >= 0.95
    assert metrics["retrieval_precision_at_expected"] >= 0.95
    assert metrics["citation_linkage"] >= 0.95
    assert metrics["numerical_consistency"] >= 0.95

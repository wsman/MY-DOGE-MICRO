import json
from pathlib import Path

from tests.eval.run_eval import run


def test_expanded_eval_cases_are_deterministic_and_cover_required_fields():
    cases_path = Path("tests/eval/cases_expanded.json")
    cases = json.loads(cases_path.read_text(encoding="utf-8"))

    result = run(cases_path)

    assert len(cases) >= 10
    assert result["case_count"] == len(cases)
    assert result["metrics"]["task_completion"] is not None
    assert result["metrics"]["tool_execution_success"] is not None
    assert result["metrics"]["citation_presence"] is not None
    assert result["metrics"]["approval_trigger_rate"] is not None
    assert result["metrics"]["latency_ms"] is not None
    assert result["metrics"]["usage_cost_record_coverage"] is not None


def test_expanded_eval_cases_include_no_portfolio_and_explicit_portfolio():
    result = run(Path("tests/eval/cases_expanded.json"))
    by_id = {item["id"]: item for item in result["results"]}

    assert "get_portfolio_exposure" not in by_id["no_portfolio_default"]["observed_tools"]
    assert "get_portfolio_exposure" in by_id["explicit_portfolio_risk"]["observed_tools"]

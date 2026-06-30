import json

from tests.eval.run_eval import run


def test_eval_runs_cases_and_reports_actual_results(tmp_path):
    cases = tmp_path / "cases.json"
    cases.write_text(json.dumps([{
        "id": "approval_case",
        "question": "Publish a high-risk memo.",
        "expected": ["approval_required", "tool_call"],
    }]), encoding="utf-8")

    result = run(cases)

    assert result["case_count"] == 1
    assert result["results"][0]["observed"]
    assert result["metrics"]["tool_execution_success"] is not None
    assert "task_completion" in result["metrics"]
    assert "citation_presence" in result["metrics"]
    assert "approval_trigger_rate" in result["metrics"]


def test_eval_reports_zero_pass_rate_when_all_fail(tmp_path):
    cases = tmp_path / "cases.json"
    cases.write_text(json.dumps([{
        "id": "impossible",
        "question": "Analyze.",
        "expected": ["impossible_flag"],
    }]), encoding="utf-8")

    result = run(cases)

    assert result["case_count"] == 1
    assert result["passed"] == 0
    assert result["results"][0]["passed"] is False


def test_eval_does_not_default_to_demo_portfolio(tmp_path):
    cases = tmp_path / "cases.json"
    cases.write_text(json.dumps([{
        "id": "no_portfolio",
        "question": "Analyze without a portfolio.",
        "expected_tools": ["stock_overview", "request_approval"],
        "forbidden_tools": ["get_portfolio_exposure"],
        "expected_artifact": True,
    }]), encoding="utf-8")

    result = run(cases)

    assert result["passed"] == 1
    assert "get_portfolio_exposure" not in result["results"][0]["observed_tools"]


def test_eval_uses_explicit_portfolio_only_when_case_provides_one(tmp_path):
    cases = tmp_path / "cases.json"
    cases.write_text(json.dumps([{
        "id": "explicit_portfolio",
        "question": "Analyze explicit portfolio exposure.",
        "portfolio_id": "portfolio-demo",
        "expected_tools": ["stock_overview", "get_portfolio_exposure", "request_approval"],
        "expected_approval": True,
        "expected_artifact": True,
    }]), encoding="utf-8")

    result = run(cases)

    assert result["passed"] == 1
    assert "get_portfolio_exposure" in result["results"][0]["observed_tools"]

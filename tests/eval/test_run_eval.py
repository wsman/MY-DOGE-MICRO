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

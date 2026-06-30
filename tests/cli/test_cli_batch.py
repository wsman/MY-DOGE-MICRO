import json

from doge.interfaces.cli.main import main


def test_cli_batch_writes_json_results(tmp_path, capsys):
    cases = tmp_path / "cases.json"
    output = tmp_path / "batch-results.json"
    cases.write_text(json.dumps([{
        "id": "batch_case",
        "question": "Analyze without a portfolio.",
        "expected_tools": ["stock_overview", "request_approval"],
        "forbidden_tools": ["get_portfolio_exposure"],
        "expected_artifact": True,
    }]), encoding="utf-8")

    main(["batch", "--cases", str(cases), "--output", str(output)])

    assert capsys.readouterr().out == ""
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["case_count"] == 1
    assert payload["results"][0]["passed"] is True
    assert "get_portfolio_exposure" not in payload["results"][0]["observed_tools"]


def test_cli_batch_prints_markdown(capsys):
    main(["batch", "--cases", "tests/eval/cases_expanded.json", "--format", "markdown"])

    out = capsys.readouterr().out
    assert "# MY-DOGE Batch Results" in out
    assert "`task_completion`" in out

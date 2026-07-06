import json

from doge.bootstrap import build_workspace_container
from doge.config import reset_settings
from doge.core.domain.platform_models import Project, ResearchCase, Workspace
from doge.interfaces.cli.main import main
from doge.platform.workspace.template_seed import BUILTIN_TEMPLATES


def test_cli_template_seed_and_list(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DOGE_AGENT_DB", str(tmp_path / "agent_state.db"))
    monkeypatch.setenv("DOGE_FEATURE_WORKFLOW_TEMPLATES", "true")
    reset_settings()

    main(["template", "seed", "--json"])
    seed_payload = json.loads(capsys.readouterr().out)
    main(["template", "list", "--json"])
    list_payload = json.loads(capsys.readouterr().out)

    expected_slugs = {item["slug"] for item in BUILTIN_TEMPLATES}
    assert "daily_market_brief" in seed_payload["inserted"]
    assert {"risk_alert", "portfolio_impact_note"}.issubset(seed_payload["inserted"])
    assert set(seed_payload["inserted"]) == expected_slugs
    assert {
        template["slug"] for template in list_payload["workflow_templates"]
    } == expected_slugs


def test_cli_case_preflight_and_execute_from_template(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DOGE_AGENT_DB", str(tmp_path / "agent_state.db"))
    monkeypatch.setenv("DOGE_FEATURE_WORKFLOW_TEMPLATES", "true")
    reset_settings()
    repo = build_workspace_container().build_platform_repository()
    workspace = Workspace.create(name="Desk")
    project = Project.create(workspace_id=workspace.workspace_id, name="Research")
    case = ResearchCase.create(project_id=project.project_id, title="NVDA earnings")
    repo.save_workspace(workspace)
    repo.save_project(project)
    repo.save_case(case)
    main(["template", "seed", "--json"])
    capsys.readouterr()

    main([
        "case",
        "preflight",
        case.case_id,
        "earnings_review",
        "--inputs",
        '{"ticker": "NVDA", "reporting_period": "2026Q1"}',
        "--json",
    ])
    preflight_payload = json.loads(capsys.readouterr().out)
    main([
        "case",
        "execute",
        case.case_id,
        "earnings_review",
        "--inputs",
        '{"ticker": "NVDA", "reporting_period": "2026Q1"}',
        "--json",
    ])
    execution_payload = json.loads(capsys.readouterr().out)
    main(["case", "review", case.case_id, "--json"])
    review_payload = json.loads(capsys.readouterr().out)

    assert preflight_payload["valid"] is True
    assert execution_payload["execution_id"].startswith("exec-")
    assert execution_payload["run_id"].startswith("run-")
    assert review_payload["executions"][0]["run_id"] == execution_payload["run_id"]

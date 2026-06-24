from pathlib import Path


def test_workspace_service_facade_is_thin_compatibility_wrapper():
    source = Path("src/doge/platform/workspace/service.py").read_text(encoding="utf-8")

    assert "class WorkspaceService" not in source
    assert "class ResearchCaseService" not in source
    assert "from doge.platform.workspace.application.case_service import" in source


def test_workspace_application_modules_export_compatible_services():
    from doge.platform.workspace import service as facade
    from doge.platform.workspace.application import (
        CaseAssetService,
        CaseDecisionService,
        CaseExecutionService,
        ProjectService,
        ResearchCaseService,
        WorkflowService,
        WorkspaceService,
    )

    assert facade.WorkspaceService is WorkspaceService
    assert facade.ProjectService is ProjectService
    assert facade.ResearchCaseService is ResearchCaseService
    assert facade.WorkflowService is WorkflowService
    assert issubclass(CaseAssetService, ResearchCaseService)
    assert issubclass(CaseDecisionService, ResearchCaseService)
    assert issubclass(CaseExecutionService, ResearchCaseService)


def test_focused_case_service_entries_expose_expected_behavior_names():
    from doge.platform.workspace.application import CaseAssetService, CaseDecisionService, CaseExecutionService

    assert hasattr(CaseAssetService, "add_case_asset")
    assert hasattr(CaseAssetService, "list_case_assets")
    assert hasattr(CaseDecisionService, "record_decision")
    assert hasattr(CaseDecisionService, "list_case_decisions")
    assert hasattr(CaseExecutionService, "execute_template")
    assert hasattr(CaseExecutionService, "preflight_template_execution")

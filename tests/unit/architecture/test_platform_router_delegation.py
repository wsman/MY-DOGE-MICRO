"""Architecture guard for platform router service delegation."""

from pathlib import Path


def test_platform_router_delegates_workspace_orchestration_to_services() -> None:
    source = Path("src/doge/interfaces/api/routers/v1/platform.py").read_text(encoding="utf-8")

    for forbidden in [
        "repo.",
        "save_workspace",
        "save_project",
        "save_case",
        "link_case_run",
        "link_workflow_template_run",
        "build_template_run_request",
        "TemplateRunInput",
        "ensure_resource_access",
        "grant_creator_access",
        "filter_accessible_resource_ids",
    ]:
        assert forbidden not in source
    for service_name in [
        "WorkspaceService",
        "ProjectService",
        "ResearchCaseService",
        "WorkflowService",
    ]:
        assert service_name in source

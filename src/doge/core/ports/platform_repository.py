"""Repository port for platform user objects and templates."""

from __future__ import annotations

from typing import Protocol

from doge.core.domain.platform_models import (
    CaseAssetLink,
    CaseDecision,
    CaseRunLink,
    Project,
    ResearchCase,
    WorkflowTemplate,
    WorkflowExecution,
    WorkflowTemplateRunLink,
    Workspace,
)


class IPlatformRepository(Protocol):
    def save_workspace(self, workspace: Workspace) -> None:
        ...

    def get_workspace(self, workspace_id: str, tenant_id: str | None = None) -> Workspace | None:
        ...

    def list_workspaces(self, limit: int = 100, tenant_id: str | None = None) -> list[Workspace]:
        ...

    def save_project(self, project: Project) -> None:
        ...

    def get_project(self, project_id: str, tenant_id: str | None = None) -> Project | None:
        ...

    def list_projects(
        self,
        *,
        workspace_id: str | None = None,
        limit: int = 100,
        tenant_id: str | None = None,
    ) -> list[Project]:
        ...

    def save_case(self, research_case: ResearchCase) -> None:
        ...

    def get_case(self, case_id: str, tenant_id: str | None = None) -> ResearchCase | None:
        ...

    def list_cases(
        self,
        *,
        project_id: str | None = None,
        limit: int = 100,
        tenant_id: str | None = None,
    ) -> list[ResearchCase]:
        ...

    def link_case_run(
        self,
        *,
        case_id: str,
        run_id: str,
        tenant_id: str | None = None,
        link_type: str = "primary",
    ) -> CaseRunLink:
        ...

    def link_workflow_template_run(
        self,
        *,
        template_id: str,
        run_id: str,
        tenant_id: str | None = None,
    ) -> WorkflowTemplateRunLink:
        ...

    def save_workflow_template(self, template: WorkflowTemplate) -> None:
        ...

    def get_workflow_template(self, template_id: str, tenant_id: str | None = None) -> WorkflowTemplate | None:
        ...

    def list_workflow_templates(self, limit: int = 100, tenant_id: str | None = None) -> list[WorkflowTemplate]:
        ...

    def save_case_asset(self, link: CaseAssetLink) -> None:
        ...

    def list_case_assets(
        self,
        case_id: str,
        tenant_id: str | None = None,
        include_deleted: bool = False,
    ) -> list[CaseAssetLink]:
        ...

    def delete_case_asset(self, asset_link_id: str, tenant_id: str | None = None) -> None:
        ...

    def save_workflow_execution(self, execution: WorkflowExecution) -> None:
        ...

    def get_workflow_execution(
        self,
        execution_id: str,
        tenant_id: str | None = None,
    ) -> WorkflowExecution | None:
        ...

    def list_workflow_executions(
        self,
        case_id: str,
        tenant_id: str | None = None,
        limit: int = 100,
    ) -> list[WorkflowExecution]:
        ...

    def update_workflow_execution_status(
        self,
        execution_id: str,
        status: str,
        *,
        run_id: str | None = None,
        preflight_result: dict | None = None,
        tenant_id: str | None = None,
    ) -> WorkflowExecution | None:
        ...

    def save_case_decision(self, decision: CaseDecision) -> None:
        ...

    def list_case_decisions(
        self,
        case_id: str,
        tenant_id: str | None = None,
        limit: int = 100,
    ) -> list[CaseDecision]:
        ...

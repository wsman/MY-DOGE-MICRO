"""Repository port for platform user objects and templates."""

from __future__ import annotations

from typing import Protocol

from doge.core.domain.platform_models import (
    CaseAssetLink,
    CaseDecision,
    CaseProgressStep,
    CaseRunLink,
    Project,
    ResearchCase,
    WorkflowTemplate,
    WorkflowExecution,
    WorkflowTemplateRunLink,
    Workspace,
)
from doge.shared.scope import TenantScope


class IPlatformRepository(Protocol):
    def save_workspace(self, workspace: Workspace, scope: TenantScope) -> None:
        ...

    def get_workspace(self, workspace_id: str, scope: TenantScope) -> Workspace | None:
        ...

    def list_workspaces(self, scope: TenantScope, limit: int = 100) -> list[Workspace]:
        ...

    def save_project(self, project: Project, scope: TenantScope) -> None:
        ...

    def get_project(self, project_id: str, scope: TenantScope) -> Project | None:
        ...

    def list_projects(
        self,
        scope: TenantScope,
        *,
        workspace_id: str | None = None,
        limit: int = 100,
    ) -> list[Project]:
        ...

    def save_case(self, research_case: ResearchCase, scope: TenantScope) -> None:
        ...

    def get_case(self, case_id: str, scope: TenantScope) -> ResearchCase | None:
        ...

    def list_cases(
        self,
        scope: TenantScope,
        *,
        project_id: str | None = None,
        limit: int = 100,
    ) -> list[ResearchCase]:
        ...

    def link_case_run(
        self,
        scope: TenantScope,
        *,
        case_id: str,
        run_id: str,
        link_type: str = "primary",
    ) -> CaseRunLink:
        ...

    def link_workflow_template_run(
        self,
        scope: TenantScope,
        *,
        template_id: str,
        run_id: str,
    ) -> WorkflowTemplateRunLink:
        ...

    def save_workflow_template(self, template: WorkflowTemplate, scope: TenantScope) -> None:
        ...

    def get_workflow_template(self, template_id: str, scope: TenantScope) -> WorkflowTemplate | None:
        ...

    def list_workflow_templates(self, scope: TenantScope, limit: int = 100) -> list[WorkflowTemplate]:
        ...

    def save_case_asset(self, link: CaseAssetLink, scope: TenantScope) -> None:
        ...

    def list_case_assets(
        self,
        scope: TenantScope,
        case_id: str,
        include_deleted: bool = False,
    ) -> list[CaseAssetLink]:
        ...

    def delete_case_asset(self, asset_link_id: str, scope: TenantScope) -> None:
        ...

    def save_workflow_execution(self, execution: WorkflowExecution, scope: TenantScope) -> None:
        ...

    def get_workflow_execution(
        self,
        execution_id: str,
        scope: TenantScope,
    ) -> WorkflowExecution | None:
        ...

    def list_workflow_executions(
        self,
        scope: TenantScope,
        case_id: str,
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
        scope: TenantScope,
    ) -> WorkflowExecution | None:
        ...

    def save_case_decision(self, decision: CaseDecision, scope: TenantScope) -> None:
        ...

    def list_case_decisions(
        self,
        scope: TenantScope,
        case_id: str,
        limit: int = 100,
    ) -> list[CaseDecision]:
        ...

    def save_case_progress_step(self, step: CaseProgressStep, scope: TenantScope) -> None:
        ...

    def list_case_progress_steps(
        self,
        scope: TenantScope,
        case_id: str,
        limit: int = 100,
    ) -> list[CaseProgressStep]:
        ...

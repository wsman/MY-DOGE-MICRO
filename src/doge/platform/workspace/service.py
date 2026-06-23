"""Workspace and workflow application services."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from doge.core.domain.agent_models import AgentRun
from doge.core.domain.enterprise_context import EnterpriseContext
from doge.core.domain.platform_models import (
    CaseRunLink,
    Project,
    ResearchCase,
    WorkflowTemplate,
    Workspace,
)
from doge.core.domain.workflow_template import TemplateRunInput, build_template_run_request
from doge.core.ports.agent_runtime import IResearchAgentRuntime
from doge.core.ports.enterprise_governance import (
    EnterpriseAclGrant,
    EnterpriseAuditEvent,
    IEnterpriseGovernanceRepository,
)
from doge.core.ports.platform_repository import IPlatformRepository


class PlatformServiceError(Exception):
    """Base error for platform workspace services."""


class PlatformNotFoundError(PlatformServiceError):
    """Requested platform object was not found."""


class PlatformAccessDeniedError(PlatformServiceError):
    """Actor is not allowed to access a platform object."""


class PlatformValidationError(PlatformServiceError):
    """Request data is structurally valid but not actionable."""


class PlatformFeatureDisabledError(PlatformServiceError):
    """A required feature flag is disabled."""


@dataclass(frozen=True)
class PlatformRequestContext:
    """Request identity and audit context for platform services."""

    enterprise_context: EnterpriseContext = field(default_factory=EnterpriseContext)
    enterprise_request: bool = False
    request_id: str | None = None

    @property
    def tenant_id(self) -> str | None:
        return self.enterprise_context.tenant_id if self.enterprise_request else None

    @property
    def user_hash(self) -> str | None:
        return self.enterprise_context.user_hash if self.enterprise_request else None


@dataclass(frozen=True)
class CaseRunCreate:
    run_id: str | None = None
    template_id: str | None = None
    link_type: str = "primary"
    question: str | None = None
    workflow: str | None = None
    session_id: str | None = None
    market: str = "us"
    language: str = "en"
    document_ids: list[str] = field(default_factory=list)
    portfolio_id: str | None = None
    model_policy: dict[str, Any] = field(default_factory=dict)
    inputs: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CaseRunCreateResult:
    link: CaseRunLink
    run: AgentRun | None = None
    template: WorkflowTemplate | None = None

    def to_dict(self) -> dict[str, Any]:
        data = dict(self.link.__dict__)
        if self.template is not None:
            data["template_id"] = self.template.template_id
            data["template_slug"] = self.template.slug
        return data


class WorkspaceService:
    """Application service for Workspace objects."""

    def __init__(self, repo: IPlatformRepository, governance: IEnterpriseGovernanceRepository) -> None:
        self._repo = repo
        self._access = PlatformAccessService(governance)

    def list(self, context: PlatformRequestContext, *, limit: int = 100) -> list[Workspace]:
        items = self._repo.list_workspaces(limit=limit, tenant_id=context.tenant_id)
        items = self._access.filter_items(context, "workspace", items, "workspace_id")
        self._access.audit(context, "workspace_list", "workspace", "*", metadata={"count": len(items)})
        return items

    def create(self, context: PlatformRequestContext, *, name: str, description: str = "") -> Workspace:
        workspace = Workspace.create(name=name, description=description, tenant_id=context.tenant_id)
        self._repo.save_workspace(workspace)
        self._access.grant_creator(context, "workspace", workspace.workspace_id, provenance="workspace_create")
        self._access.audit(context, "workspace_create", "workspace", workspace.workspace_id)
        return workspace

    def get(self, context: PlatformRequestContext, workspace_id: str) -> Workspace:
        workspace = self._repo.get_workspace(workspace_id, tenant_id=context.tenant_id)
        if workspace is None:
            raise PlatformNotFoundError("workspace not found")
        self._access.ensure(context, "workspace", workspace_id, "read")
        self._access.audit(context, "workspace_read", "workspace", workspace_id)
        return workspace


class ProjectService:
    """Application service for Project objects."""

    def __init__(self, repo: IPlatformRepository, governance: IEnterpriseGovernanceRepository) -> None:
        self._repo = repo
        self._access = PlatformAccessService(governance)

    def list(
        self,
        context: PlatformRequestContext,
        *,
        workspace_id: str | None = None,
        limit: int = 100,
    ) -> list[Project]:
        items = self._repo.list_projects(workspace_id=workspace_id, limit=limit, tenant_id=context.tenant_id)
        items = self._access.filter_items(context, "project", items, "project_id")
        self._access.audit(context, "project_list", "project", "*", metadata={"count": len(items)})
        return items

    def create(
        self,
        context: PlatformRequestContext,
        *,
        workspace_id: str,
        name: str,
        description: str = "",
        default_market: str | None = None,
    ) -> Project:
        workspace = self._repo.get_workspace(workspace_id, tenant_id=context.tenant_id)
        if workspace is None:
            raise PlatformNotFoundError("workspace not found")
        self._access.ensure(context, "workspace", workspace_id, "read")
        project = Project.create(
            workspace_id=workspace_id,
            name=name,
            description=description,
            default_market=default_market,
            tenant_id=context.tenant_id,
        )
        self._repo.save_project(project)
        self._access.grant_creator(context, "project", project.project_id, provenance="project_create")
        self._access.audit(context, "project_create", "project", project.project_id)
        return project

    def get(self, context: PlatformRequestContext, project_id: str) -> Project:
        project = self._repo.get_project(project_id, tenant_id=context.tenant_id)
        if project is None:
            raise PlatformNotFoundError("project not found")
        self._access.ensure(context, "project", project_id, "read")
        self._access.audit(context, "project_read", "project", project_id)
        return project


class ResearchCaseService:
    """Application service for Research Case objects and case-run links."""

    def __init__(
        self,
        repo: IPlatformRepository,
        governance: IEnterpriseGovernanceRepository,
        runtime: IResearchAgentRuntime,
    ) -> None:
        self._repo = repo
        self._runtime = runtime
        self._access = PlatformAccessService(governance)

    def list(
        self,
        context: PlatformRequestContext,
        *,
        project_id: str | None = None,
        limit: int = 100,
    ) -> list[ResearchCase]:
        items = self._repo.list_cases(project_id=project_id, limit=limit, tenant_id=context.tenant_id)
        items = self._access.filter_items(context, "research_case", items, "case_id")
        self._access.audit(context, "research_case_list", "research_case", "*", metadata={"count": len(items)})
        return items

    def create(
        self,
        context: PlatformRequestContext,
        *,
        project_id: str,
        title: str,
        thesis: str = "",
    ) -> ResearchCase:
        project = self._repo.get_project(project_id, tenant_id=context.tenant_id)
        if project is None:
            raise PlatformNotFoundError("project not found")
        self._access.ensure(context, "project", project_id, "read")
        research_case = ResearchCase.create(
            project_id=project_id,
            title=title,
            thesis=thesis,
            tenant_id=context.tenant_id,
        )
        self._repo.save_case(research_case)
        self._access.grant_creator(
            context,
            "research_case",
            research_case.case_id,
            provenance="research_case_create",
        )
        self._access.audit(context, "research_case_create", "research_case", research_case.case_id)
        return research_case

    def get(self, context: PlatformRequestContext, case_id: str) -> ResearchCase:
        research_case = self._repo.get_case(case_id, tenant_id=context.tenant_id)
        if research_case is None:
            raise PlatformNotFoundError("research case not found")
        self._access.ensure(context, "research_case", case_id, "read")
        self._access.audit(context, "research_case_read", "research_case", case_id)
        return research_case

    async def create_run_link(
        self,
        context: PlatformRequestContext,
        case_id: str,
        request: CaseRunCreate,
        *,
        workflow_templates_enabled: bool,
    ) -> CaseRunCreateResult:
        research_case = self._repo.get_case(case_id, tenant_id=context.tenant_id)
        if research_case is None:
            raise PlatformNotFoundError("research case not found")
        self._access.ensure(context, "research_case", case_id, "write")
        if request.run_id:
            return self._link_existing_run(context, case_id, request.run_id, request.link_type)
        if not request.template_id:
            raise PlatformValidationError("run_id or template_id required")
        if not workflow_templates_enabled:
            raise PlatformFeatureDisabledError("workflow templates API disabled")
        template = self._repo.get_workflow_template(request.template_id, tenant_id=context.tenant_id)
        if template is None:
            raise PlatformNotFoundError("workflow template not found")
        self._access.ensure(context, "workflow_template", template.template_id, "read")
        run_request = build_template_run_request(
            template,
            TemplateRunInput(
                question=request.question or research_case.title,
                workflow=request.workflow,
                session_id=request.session_id,
                market=request.market,
                language=request.language,
                document_ids=request.document_ids,
                portfolio_id=request.portfolio_id,
                model_policy=request.model_policy,
                inputs=request.inputs,
            ),
            tenant_id=context.tenant_id,
            user_hash=context.user_hash,
        )
        run = await self._runtime.create_run(run_request)
        self._repo.link_workflow_template_run(
            template_id=template.template_id,
            run_id=run.run_id,
            tenant_id=context.tenant_id,
        )
        link = self._repo.link_case_run(
            case_id=case_id,
            run_id=run.run_id,
            tenant_id=context.tenant_id,
            link_type=request.link_type,
        )
        self._access.audit(
            context,
            "research_case_run_create",
            "research_case",
            case_id,
            metadata={"run_id": run.run_id, "template_id": template.template_id},
        )
        return CaseRunCreateResult(link=link, run=run, template=template)

    def _link_existing_run(
        self,
        context: PlatformRequestContext,
        case_id: str,
        run_id: str,
        link_type: str,
    ) -> CaseRunCreateResult:
        run = self._runtime.get_run(run_id)
        if run is None:
            raise PlatformNotFoundError("run not found")
        if context.enterprise_request:
            run_tenant_id = run.model_policy.tenant_id or run.model_policy.extra.get("tenant_id")
            if run_tenant_id != context.tenant_id:
                raise PlatformNotFoundError("run not found")
        link = self._repo.link_case_run(
            case_id=case_id,
            run_id=run_id,
            tenant_id=context.tenant_id,
            link_type=link_type,
        )
        self._access.audit(
            context,
            "research_case_run_link",
            "research_case",
            case_id,
            metadata={"run_id": run_id},
        )
        return CaseRunCreateResult(link=link, run=run)


class WorkflowService:
    """Application service for Workflow Template objects."""

    def __init__(self, repo: IPlatformRepository, governance: IEnterpriseGovernanceRepository) -> None:
        self._repo = repo
        self._access = PlatformAccessService(governance)

    def list(self, context: PlatformRequestContext, *, limit: int = 100) -> list[WorkflowTemplate]:
        items = self._repo.list_workflow_templates(limit=limit, tenant_id=context.tenant_id)
        items = self._access.filter_items(context, "workflow_template", items, "template_id")
        self._access.audit(context, "workflow_template_list", "workflow_template", "*", metadata={"count": len(items)})
        return items

    def create(
        self,
        context: PlatformRequestContext,
        *,
        slug: str,
        name: str,
        description: str = "",
        current_version: str = "1",
        input_schema: dict[str, Any] | None = None,
        run_instructions: str = "",
        tool_policy: dict[str, Any] | None = None,
        evidence_policy: dict[str, Any] | None = None,
        output_contract: dict[str, Any] | None = None,
    ) -> WorkflowTemplate:
        template = WorkflowTemplate.create(
            slug=slug,
            name=name,
            description=description,
            tenant_id=context.tenant_id,
            current_version=current_version,
        )
        template = WorkflowTemplate(
            **{
                **template.__dict__,
                "input_schema": input_schema or {},
                "run_instructions": run_instructions,
                "tool_policy": tool_policy or {},
                "evidence_policy": evidence_policy or {},
                "output_contract": output_contract or {},
            }
        )
        self._repo.save_workflow_template(template)
        self._access.grant_creator(
            context,
            "workflow_template",
            template.template_id,
            provenance="workflow_template_create",
        )
        self._access.audit(context, "workflow_template_create", "workflow_template", template.template_id)
        return template

    def get(self, context: PlatformRequestContext, template_id: str) -> WorkflowTemplate:
        template = self._repo.get_workflow_template(template_id, tenant_id=context.tenant_id)
        if template is None:
            raise PlatformNotFoundError("workflow template not found")
        self._access.ensure(context, "workflow_template", template.template_id, "read")
        self._access.audit(context, "workflow_template_read", "workflow_template", template.template_id)
        return template


class PlatformAccessService:
    """Governance adapter used by workspace services."""

    def __init__(self, governance: IEnterpriseGovernanceRepository) -> None:
        self._governance = governance

    def ensure(
        self,
        context: PlatformRequestContext,
        resource_type: str,
        resource_id: str,
        permission: str,
    ) -> None:
        if not context.enterprise_request:
            return
        if self._governance.is_allowed(context.enterprise_context, resource_type, resource_id, permission):
            return
        raise PlatformAccessDeniedError(f"{resource_type} access denied")

    def filter_items(
        self,
        context: PlatformRequestContext,
        resource_type: str,
        items: list[Any],
        id_field: str,
    ) -> list[Any]:
        if not context.enterprise_request:
            return items
        resource_ids = [getattr(item, id_field) for item in items]
        allowed = self._governance.list_allowed_resource_ids(context.enterprise_context, resource_type, "read")
        if "*" in allowed:
            return items
        return [item for item in items if getattr(item, id_field) in allowed]

    def grant_creator(
        self,
        context: PlatformRequestContext,
        resource_type: str,
        resource_id: str,
        *,
        provenance: str,
    ) -> None:
        if not context.enterprise_request:
            return
        for permission in ("read", "write"):
            self._governance.grant(
                EnterpriseAclGrant(
                    tenant_id=context.enterprise_context.tenant_id,
                    subject_hash=context.enterprise_context.user_hash,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    permission=permission,
                    provenance=provenance,
                )
            )

    def audit(
        self,
        context: PlatformRequestContext,
        event_type: str,
        resource_type: str,
        resource_id: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if not context.enterprise_request:
            return
        self._governance.append_audit_event(
            EnterpriseAuditEvent(
                tenant_id=context.enterprise_context.tenant_id,
                actor_hash=context.enterprise_context.user_hash,
                event_type=event_type,
                resource_type=resource_type,
                resource_id=resource_id,
                request_id=context.request_id,
                metadata=metadata or {},
            )
        )

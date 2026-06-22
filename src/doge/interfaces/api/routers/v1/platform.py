"""v1 platform workspace, case, and workflow-template routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from doge.application.use_cases.capability_registry import BuildCapabilityRegistry
from doge.core.domain.platform_models import Project, ResearchCase, WorkflowTemplate, Workspace
from doge.core.domain.workflow_template import TemplateRunInput, build_template_run_request
from doge.core.ports.agent_runtime import IResearchAgentRuntime
from doge.core.ports.enterprise_governance import IEnterpriseGovernanceRepository
from doge.core.ports.platform_repository import IPlatformRepository
from doge.interfaces.api import deps
from doge.interfaces.api.enterprise_access import (
    append_audit,
    enterprise_context,
    ensure_resource_access,
    filter_accessible_resource_ids,
    grant_creator_access,
    is_enterprise_request,
)
from doge.interfaces.api.routers.v1._common import serialize

router = APIRouter(dependencies=[Depends(deps.require_api_token)])


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""


class ProjectCreate(BaseModel):
    workspace_id: str
    name: str = Field(min_length=1, max_length=160)
    description: str = ""
    default_market: str | None = None


class ResearchCaseCreate(BaseModel):
    project_id: str
    title: str = Field(min_length=1, max_length=200)
    thesis: str = ""


class CaseRunLinkCreate(BaseModel):
    run_id: str | None = None
    template_id: str | None = None
    link_type: str = "primary"
    question: str | None = None
    workflow: str | None = None
    session_id: str | None = None
    market: str = "us"
    language: str = "en"
    document_ids: list[str] = Field(default_factory=list)
    portfolio_id: str | None = None
    model_policy: dict[str, Any] = Field(default_factory=dict)
    inputs: dict[str, Any] = Field(default_factory=dict)


class WorkflowTemplateCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=160)
    description: str = ""
    current_version: str = "1"
    input_schema: dict[str, Any] = Field(default_factory=dict)
    run_instructions: str = ""
    tool_policy: dict[str, Any] = Field(default_factory=dict)
    evidence_policy: dict[str, Any] = Field(default_factory=dict)
    output_contract: dict[str, Any] = Field(default_factory=dict)


def _require_platform_objects(settings=Depends(deps.get_settings_dep)) -> None:
    if not settings.features.platform_objects:
        raise HTTPException(404, "platform objects API disabled")


def _require_workflow_templates(settings=Depends(deps.get_settings_dep)) -> None:
    if not settings.features.workflow_templates:
        raise HTTPException(404, "workflow templates API disabled")


def _require_capability_registry(settings=Depends(deps.get_settings_dep)) -> None:
    if not settings.features.capability_registry:
        raise HTTPException(404, "capability registry API disabled")


@router.get("/capabilities", dependencies=[Depends(_require_capability_registry)])
async def get_capabilities(
    request: Request,
    use_case: BuildCapabilityRegistry = Depends(deps.get_capability_registry_use_case),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    result = use_case.build(context=enterprise_context(request) if is_enterprise_request(request) else None)
    append_audit(
        request,
        governance,
        "capability_list",
        "capability",
        "*",
        metadata={"count": len(result["capabilities"]), "snapshot_id": result["snapshot_id"]},
    )
    return serialize(result)


@router.get("/workspaces", dependencies=[Depends(_require_platform_objects)])
async def list_workspaces(
    request: Request,
    limit: int = 100,
    repo: IPlatformRepository = Depends(deps.get_platform_repository),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    tenant_id = _tenant_id(request)
    items = repo.list_workspaces(limit=limit, tenant_id=tenant_id)
    items = _filter_items(request, governance, "workspace", items, "workspace_id")
    append_audit(request, governance, "workspace_list", "workspace", "*", metadata={"count": len(items)})
    return {"workspaces": serialize(items)}


@router.post("/workspaces", dependencies=[Depends(_require_platform_objects)], status_code=201)
async def create_workspace(
    request: Request,
    body: WorkspaceCreate,
    repo: IPlatformRepository = Depends(deps.get_platform_repository),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    workspace = Workspace.create(name=body.name, description=body.description, tenant_id=_tenant_id(request))
    repo.save_workspace(workspace)
    grant_creator_access(request, governance, "workspace", workspace.workspace_id, provenance="workspace_create")
    append_audit(request, governance, "workspace_create", "workspace", workspace.workspace_id)
    return serialize(workspace)


@router.get("/workspaces/{workspace_id}", dependencies=[Depends(_require_platform_objects)])
async def get_workspace(
    request: Request,
    workspace_id: str,
    repo: IPlatformRepository = Depends(deps.get_platform_repository),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    workspace = repo.get_workspace(workspace_id, tenant_id=_tenant_id(request))
    if workspace is None:
        raise HTTPException(404, "workspace not found")
    ensure_resource_access(request, governance, "workspace", workspace_id, "read")
    append_audit(request, governance, "workspace_read", "workspace", workspace_id)
    return serialize(workspace)


@router.get("/projects", dependencies=[Depends(_require_platform_objects)])
async def list_projects(
    request: Request,
    workspace_id: str | None = None,
    limit: int = 100,
    repo: IPlatformRepository = Depends(deps.get_platform_repository),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    items = repo.list_projects(workspace_id=workspace_id, limit=limit, tenant_id=_tenant_id(request))
    items = _filter_items(request, governance, "project", items, "project_id")
    append_audit(request, governance, "project_list", "project", "*", metadata={"count": len(items)})
    return {"projects": serialize(items)}


@router.post("/projects", dependencies=[Depends(_require_platform_objects)], status_code=201)
async def create_project(
    request: Request,
    body: ProjectCreate,
    repo: IPlatformRepository = Depends(deps.get_platform_repository),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    workspace = repo.get_workspace(body.workspace_id, tenant_id=_tenant_id(request))
    if workspace is None:
        raise HTTPException(404, "workspace not found")
    ensure_resource_access(request, governance, "workspace", body.workspace_id, "read")
    project = Project.create(
        workspace_id=body.workspace_id,
        name=body.name,
        description=body.description,
        default_market=body.default_market,
        tenant_id=_tenant_id(request),
    )
    repo.save_project(project)
    grant_creator_access(request, governance, "project", project.project_id, provenance="project_create")
    append_audit(request, governance, "project_create", "project", project.project_id)
    return serialize(project)


@router.get("/projects/{project_id}", dependencies=[Depends(_require_platform_objects)])
async def get_project(
    request: Request,
    project_id: str,
    repo: IPlatformRepository = Depends(deps.get_platform_repository),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    project = repo.get_project(project_id, tenant_id=_tenant_id(request))
    if project is None:
        raise HTTPException(404, "project not found")
    ensure_resource_access(request, governance, "project", project_id, "read")
    append_audit(request, governance, "project_read", "project", project_id)
    return serialize(project)


@router.get("/research-cases", dependencies=[Depends(_require_platform_objects)])
async def list_research_cases(
    request: Request,
    project_id: str | None = None,
    limit: int = 100,
    repo: IPlatformRepository = Depends(deps.get_platform_repository),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    items = repo.list_cases(project_id=project_id, limit=limit, tenant_id=_tenant_id(request))
    items = _filter_items(request, governance, "research_case", items, "case_id")
    append_audit(request, governance, "research_case_list", "research_case", "*", metadata={"count": len(items)})
    return {"research_cases": serialize(items)}


@router.post("/research-cases", dependencies=[Depends(_require_platform_objects)], status_code=201)
async def create_research_case(
    request: Request,
    body: ResearchCaseCreate,
    repo: IPlatformRepository = Depends(deps.get_platform_repository),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    project = repo.get_project(body.project_id, tenant_id=_tenant_id(request))
    if project is None:
        raise HTTPException(404, "project not found")
    ensure_resource_access(request, governance, "project", body.project_id, "read")
    research_case = ResearchCase.create(
        project_id=body.project_id,
        title=body.title,
        thesis=body.thesis,
        tenant_id=_tenant_id(request),
    )
    repo.save_case(research_case)
    grant_creator_access(request, governance, "research_case", research_case.case_id, provenance="research_case_create")
    append_audit(request, governance, "research_case_create", "research_case", research_case.case_id)
    return serialize(research_case)


@router.get("/research-cases/{case_id}", dependencies=[Depends(_require_platform_objects)])
async def get_research_case(
    request: Request,
    case_id: str,
    repo: IPlatformRepository = Depends(deps.get_platform_repository),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    research_case = repo.get_case(case_id, tenant_id=_tenant_id(request))
    if research_case is None:
        raise HTTPException(404, "research case not found")
    ensure_resource_access(request, governance, "research_case", case_id, "read")
    append_audit(request, governance, "research_case_read", "research_case", case_id)
    return serialize(research_case)


@router.post("/research-cases/{case_id}/runs", dependencies=[Depends(_require_platform_objects)], status_code=201)
async def link_research_case_run(
    request: Request,
    case_id: str,
    body: CaseRunLinkCreate,
    repo: IPlatformRepository = Depends(deps.get_platform_repository),
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
    settings=Depends(deps.get_settings_dep),
):
    research_case = repo.get_case(case_id, tenant_id=_tenant_id(request))
    if research_case is None:
        raise HTTPException(404, "research case not found")
    ensure_resource_access(request, governance, "research_case", case_id, "write")
    if body.run_id:
        run = runtime.get_run(body.run_id)
        if run is None:
            raise HTTPException(404, "run not found")
        if is_enterprise_request(request):
            run_tenant_id = run.model_policy.tenant_id or run.model_policy.extra.get("tenant_id")
            if run_tenant_id != enterprise_context(request).tenant_id:
                raise HTTPException(404, "run not found")
        link = repo.link_case_run(
            case_id=case_id,
            run_id=body.run_id,
            tenant_id=_tenant_id(request),
            link_type=body.link_type,
        )
        append_audit(
            request,
            governance,
            "research_case_run_link",
            "research_case",
            case_id,
            metadata={"run_id": body.run_id},
        )
        return serialize(link)
    if not body.template_id:
        raise HTTPException(400, "run_id or template_id required")
    if not settings.features.workflow_templates:
        raise HTTPException(404, "workflow templates API disabled")
    template = repo.get_workflow_template(body.template_id, tenant_id=_tenant_id(request))
    if template is None:
        raise HTTPException(404, "workflow template not found")
    ensure_resource_access(request, governance, "workflow_template", template.template_id, "read")
    run_request = build_template_run_request(
        template,
        TemplateRunInput(
            question=body.question or research_case.title,
            workflow=body.workflow,
            session_id=body.session_id,
            market=body.market,
            language=body.language,
            document_ids=body.document_ids,
            portfolio_id=body.portfolio_id,
            model_policy=body.model_policy,
            inputs=body.inputs,
        ),
        tenant_id=_tenant_id(request),
        user_hash=enterprise_context(request).user_hash if is_enterprise_request(request) else None,
    )
    run = await runtime.create_run(run_request)
    repo.link_workflow_template_run(template_id=template.template_id, run_id=run.run_id, tenant_id=_tenant_id(request))
    link = repo.link_case_run(case_id=case_id, run_id=run.run_id, tenant_id=_tenant_id(request), link_type=body.link_type)
    append_audit(
        request,
        governance,
        "research_case_run_create",
        "research_case",
        case_id,
        metadata={"run_id": run.run_id, "template_id": template.template_id},
    )
    response = serialize(link)
    response["template_id"] = template.template_id
    response["template_slug"] = template.slug
    return response


@router.get("/workflow-templates", dependencies=[Depends(_require_workflow_templates)])
async def list_workflow_templates(
    request: Request,
    limit: int = 100,
    repo: IPlatformRepository = Depends(deps.get_platform_repository),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    items = repo.list_workflow_templates(limit=limit, tenant_id=_tenant_id(request))
    items = _filter_items(request, governance, "workflow_template", items, "template_id")
    append_audit(request, governance, "workflow_template_list", "workflow_template", "*", metadata={"count": len(items)})
    return {"workflow_templates": serialize(items)}


@router.post("/workflow-templates", dependencies=[Depends(_require_workflow_templates)], status_code=201)
async def create_workflow_template(
    request: Request,
    body: WorkflowTemplateCreate,
    repo: IPlatformRepository = Depends(deps.get_platform_repository),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    template = WorkflowTemplate.create(
        slug=body.slug,
        name=body.name,
        description=body.description,
        tenant_id=_tenant_id(request),
        current_version=body.current_version,
    )
    template = WorkflowTemplate(
        **{
            **template.__dict__,
            "input_schema": body.input_schema,
            "run_instructions": body.run_instructions,
            "tool_policy": body.tool_policy,
            "evidence_policy": body.evidence_policy,
            "output_contract": body.output_contract,
        }
    )
    repo.save_workflow_template(template)
    grant_creator_access(request, governance, "workflow_template", template.template_id, provenance="workflow_template_create")
    append_audit(request, governance, "workflow_template_create", "workflow_template", template.template_id)
    return serialize(template)


@router.get("/workflow-templates/{template_id}", dependencies=[Depends(_require_workflow_templates)])
async def get_workflow_template(
    request: Request,
    template_id: str,
    repo: IPlatformRepository = Depends(deps.get_platform_repository),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    template = repo.get_workflow_template(template_id, tenant_id=_tenant_id(request))
    if template is None:
        raise HTTPException(404, "workflow template not found")
    ensure_resource_access(request, governance, "workflow_template", template.template_id, "read")
    append_audit(request, governance, "workflow_template_read", "workflow_template", template.template_id)
    return serialize(template)


def _tenant_id(request: Request) -> str | None:
    return enterprise_context(request).tenant_id if is_enterprise_request(request) else None


def _filter_items(
    request: Request,
    governance: IEnterpriseGovernanceRepository,
    resource_type: str,
    items: list[Any],
    id_field: str,
) -> list[Any]:
    if not is_enterprise_request(request):
        return items
    resource_ids = [getattr(item, id_field) for item in items]
    allowed = filter_accessible_resource_ids(request, governance, resource_type, resource_ids, "read")
    return [item for item in items if getattr(item, id_field) in allowed]

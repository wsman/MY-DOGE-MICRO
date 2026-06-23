"""v1 platform workspace, case, and workflow-template routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from doge.application.use_cases.capability_registry import BuildCapabilityRegistry
from doge.application.use_cases.run_summary import BuildRunSummary
from doge.application.agent.worker import AsyncioWorker
from doge.core.ports.agent_runtime import IResearchAgentRuntime
from doge.core.ports.document_repository import IDocumentRepository
from doge.core.ports.enterprise_governance import IEnterpriseGovernanceRepository
from doge.core.ports.portfolio_repository import IPortfolioRepository
from doge.core.ports.platform_repository import IPlatformRepository
from doge.interfaces.api import deps
from doge.interfaces.api.enterprise_access import (
    append_audit,
    enterprise_context,
    is_enterprise_request,
    redact_run_summary_for_request,
    request_id,
)
from doge.interfaces.api.routers.v1._common import serialize
from doge.platform.workspace import (
    CaseAssetCreate,
    CaseDecisionCreate,
    CaseExecutionCreate,
    CaseRunCreate,
    PlatformAccessDeniedError,
    PlatformFeatureDisabledError,
    PlatformNotFoundError,
    PlatformRequestContext,
    PlatformServiceError,
    PlatformValidationError,
    ProjectService,
    ResearchCaseService,
    WorkflowService,
    WorkspaceService,
)

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


class CaseAssetCreateRequest(BaseModel):
    asset_type: str
    asset_id: str
    asset_name: str = ""
    role: str = "source"
    version: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CaseDecisionCreateRequest(BaseModel):
    decision_type: str
    rationale: str = ""
    source_run_ids: list[str] = Field(default_factory=list)
    source_execution_ids: list[str] = Field(default_factory=list)


class CaseExecutionRequest(BaseModel):
    template_id: str
    question: str | None = None
    workflow: str | None = None
    session_id: str | None = None
    market: str = "us"
    language: str = "en"
    document_ids: list[str] = Field(default_factory=list)
    portfolio_id: str | None = None
    asset_link_ids: list[str] = Field(default_factory=list)
    model_policy: dict[str, Any] = Field(default_factory=dict)
    inputs: dict[str, Any] = Field(default_factory=dict)
    skip_preflight: bool = False
    trigger_channel: str = "api"


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
    metadata: dict[str, Any] = Field(default_factory=dict)
    required_capabilities: list[str] | None = None
    eval_policy: list[str] | None = None
    approval_policy: dict[str, Any] | None = None
    ui_schema: dict[str, Any] | None = None


def _require_platform_objects(settings=Depends(deps.get_settings_dep)) -> None:
    if not settings.features.platform_objects:
        raise HTTPException(404, "platform objects API disabled")


def _require_workflow_templates(settings=Depends(deps.get_settings_dep)) -> None:
    if not settings.features.workflow_templates:
        raise HTTPException(404, "workflow templates API disabled")


def _require_capability_registry(settings=Depends(deps.get_settings_dep)) -> None:
    if not settings.features.capability_registry:
        raise HTTPException(404, "capability registry API disabled")


def _workspace_service(
    repo: IPlatformRepository = Depends(deps.get_platform_repository),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
) -> WorkspaceService:
    return WorkspaceService(repo, governance)


def _project_service(
    repo: IPlatformRepository = Depends(deps.get_platform_repository),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
) -> ProjectService:
    return ProjectService(repo, governance)


def _research_case_service(
    repo: IPlatformRepository = Depends(deps.get_platform_repository),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
) -> ResearchCaseService:
    return ResearchCaseService(repo, governance, runtime)


def _research_case_execution_service(
    repo: IPlatformRepository = Depends(deps.get_platform_repository),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
    documents: IDocumentRepository = Depends(deps.get_agent_document_repository),
    portfolios: IPortfolioRepository = Depends(deps.get_portfolio_repository),
    capability_registry: BuildCapabilityRegistry = Depends(deps.get_capability_registry_use_case),
    settings=Depends(deps.get_settings_dep),
) -> ResearchCaseService:
    return ResearchCaseService(
        repo,
        governance,
        runtime,
        document_repository=documents,
        portfolio_repository=portfolios,
        capability_registry=capability_registry,
        capability_registry_enabled=settings.features.capability_registry,
    )


def _workflow_service(
    repo: IPlatformRepository = Depends(deps.get_platform_repository),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
) -> WorkflowService:
    return WorkflowService(repo, governance)


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


@router.get("/home-queue", dependencies=[Depends(_require_platform_objects)])
async def get_home_queue(
    request: Request,
    limit: int = 20,
    service: ResearchCaseService = Depends(_research_case_execution_service),
):
    try:
        return serialize(service.build_home_queue(_platform_context(request), limit=limit))
    except PlatformServiceError as exc:
        _raise_platform_error(exc)


@router.get("/workspaces", dependencies=[Depends(_require_platform_objects)])
async def list_workspaces(
    request: Request,
    limit: int = 100,
    service: WorkspaceService = Depends(_workspace_service),
):
    try:
        items = service.list(_platform_context(request), limit=limit)
        return {"workspaces": serialize(items)}
    except PlatformServiceError as exc:
        _raise_platform_error(exc)


@router.post("/workspaces", dependencies=[Depends(_require_platform_objects)], status_code=201)
async def create_workspace(
    request: Request,
    body: WorkspaceCreate,
    service: WorkspaceService = Depends(_workspace_service),
):
    try:
        workspace = service.create(_platform_context(request), name=body.name, description=body.description)
        return serialize(workspace)
    except PlatformServiceError as exc:
        _raise_platform_error(exc)


@router.get("/workspaces/{workspace_id}", dependencies=[Depends(_require_platform_objects)])
async def get_workspace(
    request: Request,
    workspace_id: str,
    service: WorkspaceService = Depends(_workspace_service),
):
    try:
        return serialize(service.get(_platform_context(request), workspace_id))
    except PlatformServiceError as exc:
        _raise_platform_error(exc)


@router.get("/projects", dependencies=[Depends(_require_platform_objects)])
async def list_projects(
    request: Request,
    workspace_id: str | None = None,
    limit: int = 100,
    service: ProjectService = Depends(_project_service),
):
    try:
        items = service.list(_platform_context(request), workspace_id=workspace_id, limit=limit)
        return {"projects": serialize(items)}
    except PlatformServiceError as exc:
        _raise_platform_error(exc)


@router.post("/projects", dependencies=[Depends(_require_platform_objects)], status_code=201)
async def create_project(
    request: Request,
    body: ProjectCreate,
    service: ProjectService = Depends(_project_service),
):
    try:
        project = service.create(
            _platform_context(request),
            workspace_id=body.workspace_id,
            name=body.name,
            description=body.description,
            default_market=body.default_market,
        )
        return serialize(project)
    except PlatformServiceError as exc:
        _raise_platform_error(exc)


@router.get("/projects/{project_id}", dependencies=[Depends(_require_platform_objects)])
async def get_project(
    request: Request,
    project_id: str,
    service: ProjectService = Depends(_project_service),
):
    try:
        return serialize(service.get(_platform_context(request), project_id))
    except PlatformServiceError as exc:
        _raise_platform_error(exc)


@router.get("/research-cases", dependencies=[Depends(_require_platform_objects)])
async def list_research_cases(
    request: Request,
    project_id: str | None = None,
    limit: int = 100,
    service: ResearchCaseService = Depends(_research_case_service),
):
    try:
        items = service.list(_platform_context(request), project_id=project_id, limit=limit)
        return {"research_cases": serialize(items)}
    except PlatformServiceError as exc:
        _raise_platform_error(exc)


@router.post("/research-cases", dependencies=[Depends(_require_platform_objects)], status_code=201)
async def create_research_case(
    request: Request,
    body: ResearchCaseCreate,
    service: ResearchCaseService = Depends(_research_case_service),
):
    try:
        research_case = service.create(
            _platform_context(request),
            project_id=body.project_id,
            title=body.title,
            thesis=body.thesis,
        )
        return serialize(research_case)
    except PlatformServiceError as exc:
        _raise_platform_error(exc)


@router.get("/research-cases/{case_id}", dependencies=[Depends(_require_platform_objects)])
async def get_research_case(
    request: Request,
    case_id: str,
    service: ResearchCaseService = Depends(_research_case_service),
):
    try:
        return serialize(service.get(_platform_context(request), case_id))
    except PlatformServiceError as exc:
        _raise_platform_error(exc)


@router.get("/research-cases/{case_id}/assets", dependencies=[Depends(_require_platform_objects)])
async def list_research_case_assets(
    request: Request,
    case_id: str,
    service: ResearchCaseService = Depends(_research_case_execution_service),
):
    try:
        return {"assets": serialize(service.list_case_assets(_platform_context(request), case_id))}
    except PlatformServiceError as exc:
        _raise_platform_error(exc)


@router.post("/research-cases/{case_id}/assets", dependencies=[Depends(_require_platform_objects)], status_code=201)
async def add_research_case_asset(
    request: Request,
    case_id: str,
    body: CaseAssetCreateRequest,
    service: ResearchCaseService = Depends(_research_case_execution_service),
):
    try:
        return serialize(service.add_case_asset(
            _platform_context(request),
            case_id,
            CaseAssetCreate(
                asset_type=body.asset_type,
                asset_id=body.asset_id,
                asset_name=body.asset_name,
                role=body.role,
                version=body.version,
                metadata=body.metadata,
            ),
        ))
    except PlatformServiceError as exc:
        _raise_platform_error(exc)


@router.delete("/research-cases/{case_id}/assets/{asset_link_id}", dependencies=[Depends(_require_platform_objects)])
async def remove_research_case_asset(
    request: Request,
    case_id: str,
    asset_link_id: str,
    service: ResearchCaseService = Depends(_research_case_execution_service),
):
    try:
        service.remove_case_asset(_platform_context(request), case_id, asset_link_id)
        return {"status": "deleted", "asset_link_id": asset_link_id}
    except PlatformServiceError as exc:
        _raise_platform_error(exc)


@router.get("/research-cases/{case_id}/decisions", dependencies=[Depends(_require_platform_objects)])
async def list_research_case_decisions(
    request: Request,
    case_id: str,
    service: ResearchCaseService = Depends(_research_case_execution_service),
):
    try:
        return {"decisions": serialize(service.list_case_decisions(_platform_context(request), case_id))}
    except PlatformServiceError as exc:
        _raise_platform_error(exc)


@router.post("/research-cases/{case_id}/decisions", dependencies=[Depends(_require_platform_objects)], status_code=201)
async def record_research_case_decision(
    request: Request,
    case_id: str,
    body: CaseDecisionCreateRequest,
    service: ResearchCaseService = Depends(_research_case_execution_service),
):
    try:
        return serialize(service.record_decision(
            _platform_context(request),
            case_id,
            CaseDecisionCreate(
                decision_type=body.decision_type,
                rationale=body.rationale,
                source_run_ids=body.source_run_ids,
                source_execution_ids=body.source_execution_ids,
            ),
        ))
    except PlatformServiceError as exc:
        _raise_platform_error(exc)


@router.post(
    "/research-cases/{case_id}/executions/preflight",
    dependencies=[Depends(_require_platform_objects)],
)
async def preflight_research_case_execution(
    request: Request,
    case_id: str,
    body: CaseExecutionRequest,
    service: ResearchCaseService = Depends(_research_case_execution_service),
    settings=Depends(deps.get_settings_dep),
):
    try:
        result = service.preflight_template_execution(
            _platform_context(request),
            case_id,
            _case_execution_create(body),
            workflow_templates_enabled=settings.features.workflow_templates,
        )
        return serialize(result.to_dict())
    except PlatformServiceError as exc:
        _raise_platform_error(exc)


@router.post(
    "/research-cases/{case_id}/executions",
    dependencies=[Depends(_require_platform_objects)],
    status_code=202,
)
async def execute_research_case_template(
    request: Request,
    case_id: str,
    body: CaseExecutionRequest,
    service: ResearchCaseService = Depends(_research_case_execution_service),
    worker: AsyncioWorker = Depends(deps.get_daemon_worker),
    settings=Depends(deps.get_settings_dep),
):
    try:
        result = await service.execute_template(
            _platform_context(request),
            case_id,
            _case_execution_create(body),
            workflow_templates_enabled=settings.features.workflow_templates,
            worker=worker,
        )
        return serialize(result.to_dict())
    except PlatformServiceError as exc:
        _raise_platform_error(exc)


@router.get("/research-cases/{case_id}/executions", dependencies=[Depends(_require_platform_objects)])
async def list_research_case_executions(
    request: Request,
    case_id: str,
    limit: int = 100,
    service: ResearchCaseService = Depends(_research_case_execution_service),
):
    try:
        items = service.list_workflow_executions_for_case(_platform_context(request), case_id, limit=limit)
        return {"executions": serialize(items)}
    except PlatformServiceError as exc:
        _raise_platform_error(exc)


@router.get(
    "/research-cases/{case_id}/executions/{execution_id}",
    dependencies=[Depends(_require_platform_objects)],
)
async def get_research_case_execution(
    request: Request,
    case_id: str,
    execution_id: str,
    service: ResearchCaseService = Depends(_research_case_execution_service),
):
    try:
        return serialize(service.get_workflow_execution(_platform_context(request), case_id, execution_id))
    except PlatformServiceError as exc:
        _raise_platform_error(exc)


@router.get("/research-cases/{case_id}/review", dependencies=[Depends(_require_platform_objects)])
async def get_research_case_review(
    request: Request,
    case_id: str,
    service: ResearchCaseService = Depends(_research_case_execution_service),
    settings=Depends(deps.get_settings_dep),
    use_case: BuildRunSummary = Depends(deps.get_run_summary_use_case),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    try:
        review = service.build_case_review(_platform_context(request), case_id)
        latest_run = review.get("latest_run")
        if latest_run is not None and settings.features.run_summary_api:
            summary_resources = _build_summary_for_review(request, latest_run, use_case, governance)
            review.update(summary_resources)
        else:
            review.update({"summary": None, "claims": [], "citations": [], "eval": None})
            if latest_run is not None:
                review["warnings"] = [*review.get("warnings", []), "run_summary_api_unavailable"]
        return serialize(review)
    except PlatformServiceError as exc:
        _raise_platform_error(exc)


@router.post("/research-cases/{case_id}/runs", dependencies=[Depends(_require_platform_objects)], status_code=201)
async def link_research_case_run(
    request: Request,
    case_id: str,
    body: CaseRunLinkCreate,
    service: ResearchCaseService = Depends(_research_case_service),
    settings=Depends(deps.get_settings_dep),
):
    try:
        result = await service.create_run_link(
            _platform_context(request),
            case_id,
            CaseRunCreate(
                run_id=body.run_id,
                template_id=body.template_id,
                link_type=body.link_type,
                question=body.question,
                workflow=body.workflow,
                session_id=body.session_id,
                market=body.market,
                language=body.language,
                document_ids=body.document_ids,
                portfolio_id=body.portfolio_id,
                model_policy=body.model_policy,
                inputs=body.inputs,
            ),
            workflow_templates_enabled=settings.features.workflow_templates,
        )
        return serialize(result.to_dict())
    except PlatformServiceError as exc:
        _raise_platform_error(exc)


@router.get("/workflow-templates", dependencies=[Depends(_require_workflow_templates)])
async def list_workflow_templates(
    request: Request,
    limit: int = 100,
    service: WorkflowService = Depends(_workflow_service),
):
    try:
        items = service.list(_platform_context(request), limit=limit)
        return {"workflow_templates": serialize(items)}
    except PlatformServiceError as exc:
        _raise_platform_error(exc)


@router.post("/workflow-templates", dependencies=[Depends(_require_workflow_templates)], status_code=201)
async def create_workflow_template(
    request: Request,
    body: WorkflowTemplateCreate,
    service: WorkflowService = Depends(_workflow_service),
):
    try:
        template = service.create(
            _platform_context(request),
            slug=body.slug,
            name=body.name,
            description=body.description,
            current_version=body.current_version,
            input_schema=body.input_schema,
            run_instructions=body.run_instructions,
            tool_policy=body.tool_policy,
            evidence_policy=body.evidence_policy,
            output_contract=body.output_contract,
            metadata=body.metadata,
            required_capabilities=body.required_capabilities,
            eval_policy=body.eval_policy,
            approval_policy=body.approval_policy,
            ui_schema=body.ui_schema,
        )
        return serialize(template)
    except PlatformServiceError as exc:
        _raise_platform_error(exc)


@router.get("/workflow-templates/{template_id}", dependencies=[Depends(_require_workflow_templates)])
async def get_workflow_template(
    request: Request,
    template_id: str,
    service: WorkflowService = Depends(_workflow_service),
):
    try:
        return serialize(service.get(_platform_context(request), template_id))
    except PlatformServiceError as exc:
        _raise_platform_error(exc)


def _platform_context(request: Request) -> PlatformRequestContext:
    return PlatformRequestContext(
        enterprise_context=enterprise_context(request),
        enterprise_request=is_enterprise_request(request),
        request_id=request_id(request),
    )


def _case_execution_create(body: CaseExecutionRequest) -> CaseExecutionCreate:
    return CaseExecutionCreate(
        template_id=body.template_id,
        question=body.question,
        workflow=body.workflow,
        session_id=body.session_id,
        market=body.market,
        language=body.language,
        document_ids=body.document_ids,
        portfolio_id=body.portfolio_id,
        asset_link_ids=body.asset_link_ids,
        model_policy=body.model_policy,
        inputs=body.inputs,
        skip_preflight=body.skip_preflight,
        trigger_channel=body.trigger_channel,
    )


def _build_summary_for_review(
    request: Request,
    run,
    use_case: BuildRunSummary,
    governance: IEnterpriseGovernanceRepository,
) -> dict[str, Any]:
    tenant_id = enterprise_context(request).tenant_id if is_enterprise_request(request) else None
    result = use_case.build(run, tenant_id=tenant_id)
    result = redact_run_summary_for_request(request, governance, result)
    append_audit(request, governance, "research_case_review_read", "research_case", run.run_id)
    return {
        "summary": result["summary"],
        "claims": result["claims"],
        "citations": result["citations"],
        "eval": result["eval"],
    }


def _raise_platform_error(exc: PlatformServiceError) -> None:
    if isinstance(exc, PlatformAccessDeniedError):
        raise HTTPException(403, str(exc))
    if isinstance(exc, PlatformValidationError):
        if getattr(exc, "details", None):
            raise HTTPException(400, {"message": str(exc), "details": exc.details})
        raise HTTPException(400, str(exc))
    if isinstance(exc, (PlatformFeatureDisabledError, PlatformNotFoundError)):
        raise HTTPException(404, str(exc))
    raise HTTPException(500, "platform service error")

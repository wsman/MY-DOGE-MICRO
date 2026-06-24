"""v1 research-case execution, review, and run-link routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from doge.application.use_cases.run_summary import BuildRunSummary
from doge.application.agent.worker import AsyncioWorker
from doge.core.ports.enterprise_governance import IEnterpriseGovernanceRepository
from doge.interfaces.api import deps
from doge.interfaces.api.enterprise_access import (
    append_audit,
    enterprise_context,
    is_enterprise_request,
    redact_run_summary_for_request,
)
from doge.interfaces.api.routers.v1._common import serialize
from doge.interfaces.api.routers.v1._platform_common import (
    build_research_case_execution_service,
    build_research_case_service,
    platform_context,
    raise_platform_error,
    require_platform_objects,
)
from doge.platform.workspace import (
    CaseExecutionCreate,
    CaseRunCreate,
    PlatformServiceError,
    ResearchCaseService,
)

router = APIRouter(dependencies=[Depends(deps.require_api_token)])


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


@router.post(
    "/research-cases/{case_id}/executions/preflight",
    dependencies=[Depends(require_platform_objects)],
)
async def preflight_research_case_execution(
    request: Request,
    case_id: str,
    body: CaseExecutionRequest,
    service: ResearchCaseService = Depends(build_research_case_execution_service),
    settings=Depends(deps.get_settings_dep),
):
    try:
        result = service.preflight_template_execution(
            platform_context(request),
            case_id,
            _case_execution_create(body),
            workflow_templates_enabled=settings.features.workflow_templates,
        )
        return serialize(result.to_dict())
    except PlatformServiceError as exc:
        raise_platform_error(exc)


@router.post(
    "/research-cases/{case_id}/executions",
    dependencies=[Depends(require_platform_objects)],
    status_code=202,
)
async def execute_research_case_template(
    request: Request,
    case_id: str,
    body: CaseExecutionRequest,
    service: ResearchCaseService = Depends(build_research_case_execution_service),
    worker: AsyncioWorker = Depends(deps.get_daemon_worker),
    settings=Depends(deps.get_settings_dep),
):
    try:
        result = await service.execute_template(
            platform_context(request),
            case_id,
            _case_execution_create(body),
            workflow_templates_enabled=settings.features.workflow_templates,
            worker=worker,
        )
        return serialize(result.to_dict())
    except PlatformServiceError as exc:
        raise_platform_error(exc)


@router.get("/research-cases/{case_id}/executions", dependencies=[Depends(require_platform_objects)])
async def list_research_case_executions(
    request: Request,
    case_id: str,
    limit: int = 100,
    service: ResearchCaseService = Depends(build_research_case_execution_service),
):
    try:
        items = service.list_workflow_executions_for_case(platform_context(request), case_id, limit=limit)
        return {"executions": serialize(items)}
    except PlatformServiceError as exc:
        raise_platform_error(exc)


@router.get(
    "/research-cases/{case_id}/executions/{execution_id}",
    dependencies=[Depends(require_platform_objects)],
)
async def get_research_case_execution(
    request: Request,
    case_id: str,
    execution_id: str,
    service: ResearchCaseService = Depends(build_research_case_execution_service),
):
    try:
        return serialize(service.get_workflow_execution(platform_context(request), case_id, execution_id))
    except PlatformServiceError as exc:
        raise_platform_error(exc)


@router.get("/research-cases/{case_id}/review", dependencies=[Depends(require_platform_objects)])
async def get_research_case_review(
    request: Request,
    case_id: str,
    service: ResearchCaseService = Depends(build_research_case_execution_service),
    settings=Depends(deps.get_settings_dep),
    use_case: BuildRunSummary = Depends(deps.get_run_summary_use_case),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    try:
        review = service.build_case_review(platform_context(request), case_id)
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
        raise_platform_error(exc)


@router.post("/research-cases/{case_id}/runs", dependencies=[Depends(require_platform_objects)], status_code=201)
async def link_research_case_run(
    request: Request,
    case_id: str,
    body: CaseRunLinkCreate,
    service: ResearchCaseService = Depends(build_research_case_service),
    settings=Depends(deps.get_settings_dep),
):
    try:
        result = await service.create_run_link(
            platform_context(request),
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
        raise_platform_error(exc)


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

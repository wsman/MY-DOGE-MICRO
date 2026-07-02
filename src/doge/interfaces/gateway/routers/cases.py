"""v1 research-case, case-asset/decision and home-queue routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from doge.interfaces.api import deps
from doge.interfaces.api.handlers import ResearchCaseHandler
from doge.interfaces.gateway.routers._common import serialize
from doge.interfaces.gateway.routers._response_models import (
    CaseDecisionListResponse,
    ResearchCaseListResponse,
    ResearchCaseResponse,
)
from doge.interfaces.gateway.routers._platform_common import (
    build_research_case_execution_service,
    build_research_case_service,
    platform_context,
    raise_platform_error,
    require_platform_objects,
)
from doge.platform.workspace import (
    CaseAssetCreate,
    CaseDecisionCreate,
    PlatformServiceError,
    ResearchCaseService,
)

router = APIRouter(dependencies=[Depends(deps.require_api_token)])


class ResearchCaseCreate(BaseModel):
    project_id: str
    title: str = Field(min_length=1, max_length=200)
    thesis: str = ""


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


@router.get("/home-queue", dependencies=[Depends(require_platform_objects)])
async def get_home_queue(
    request: Request,
    limit: int = 20,
    service: ResearchCaseService = Depends(build_research_case_execution_service),
):
    try:
        return serialize(
            ResearchCaseHandler(service=service).home_queue(
                context=platform_context(request),
                limit=limit,
            )
        )
    except PlatformServiceError as exc:
        raise_platform_error(exc)


@router.get(
    "/research-cases",
    response_model=ResearchCaseListResponse,
    dependencies=[Depends(require_platform_objects)],
)
async def list_research_cases(
    request: Request,
    project_id: str | None = None,
    limit: int = 100,
    service: ResearchCaseService = Depends(build_research_case_service),
):
    try:
        items = ResearchCaseHandler(service=service).list(
            context=platform_context(request),
            project_id=project_id,
            limit=limit,
        )
        return {"research_cases": serialize(items)}
    except PlatformServiceError as exc:
        raise_platform_error(exc)


@router.post("/research-cases", dependencies=[Depends(require_platform_objects)], status_code=201)
async def create_research_case(
    request: Request,
    body: ResearchCaseCreate,
    service: ResearchCaseService = Depends(build_research_case_service),
):
    try:
        research_case = ResearchCaseHandler(service=service).create(
            context=platform_context(request),
            project_id=body.project_id,
            title=body.title,
            thesis=body.thesis,
        )
        return serialize(research_case)
    except PlatformServiceError as exc:
        raise_platform_error(exc)


@router.get(
    "/research-cases/{case_id}",
    response_model=ResearchCaseResponse,
    dependencies=[Depends(require_platform_objects)],
)
async def get_research_case(
    request: Request,
    case_id: str,
    service: ResearchCaseService = Depends(build_research_case_service),
):
    try:
        research_case = ResearchCaseHandler(service=service).get(
            context=platform_context(request),
            case_id=case_id,
        )
        return serialize(research_case)
    except PlatformServiceError as exc:
        raise_platform_error(exc)


@router.get("/research-cases/{case_id}/assets", dependencies=[Depends(require_platform_objects)])
async def list_research_case_assets(
    request: Request,
    case_id: str,
    service: ResearchCaseService = Depends(build_research_case_execution_service),
):
    try:
        assets = ResearchCaseHandler(service=service).list_assets(
            context=platform_context(request),
            case_id=case_id,
        )
        return {"assets": serialize(assets)}
    except PlatformServiceError as exc:
        raise_platform_error(exc)


@router.post("/research-cases/{case_id}/assets", dependencies=[Depends(require_platform_objects)], status_code=201)
async def add_research_case_asset(
    request: Request,
    case_id: str,
    body: CaseAssetCreateRequest,
    service: ResearchCaseService = Depends(build_research_case_execution_service),
):
    try:
        asset = ResearchCaseHandler(service=service).add_asset(
            context=platform_context(request),
            case_id=case_id,
            command=CaseAssetCreate(
                asset_type=body.asset_type,
                asset_id=body.asset_id,
                asset_name=body.asset_name,
                role=body.role,
                version=body.version,
                metadata=body.metadata,
            ),
        )
        return serialize(asset)
    except PlatformServiceError as exc:
        raise_platform_error(exc)


@router.delete("/research-cases/{case_id}/assets/{asset_link_id}", dependencies=[Depends(require_platform_objects)])
async def remove_research_case_asset(
    request: Request,
    case_id: str,
    asset_link_id: str,
    service: ResearchCaseService = Depends(build_research_case_execution_service),
):
    try:
        ResearchCaseHandler(service=service).remove_asset(
            context=platform_context(request),
            case_id=case_id,
            asset_link_id=asset_link_id,
        )
        return {"status": "deleted", "asset_link_id": asset_link_id}
    except PlatformServiceError as exc:
        raise_platform_error(exc)


@router.get(
    "/research-cases/{case_id}/decisions",
    response_model=CaseDecisionListResponse,
    dependencies=[Depends(require_platform_objects)],
)
async def list_research_case_decisions(
    request: Request,
    case_id: str,
    service: ResearchCaseService = Depends(build_research_case_execution_service),
):
    try:
        decisions = ResearchCaseHandler(service=service).list_decisions(
            context=platform_context(request),
            case_id=case_id,
        )
        return {"decisions": serialize(decisions)}
    except PlatformServiceError as exc:
        raise_platform_error(exc)


@router.post("/research-cases/{case_id}/decisions", dependencies=[Depends(require_platform_objects)], status_code=201)
async def record_research_case_decision(
    request: Request,
    case_id: str,
    body: CaseDecisionCreateRequest,
    service: ResearchCaseService = Depends(build_research_case_execution_service),
):
    try:
        decision = ResearchCaseHandler(service=service).record_decision(
            context=platform_context(request),
            case_id=case_id,
            command=CaseDecisionCreate(
                decision_type=body.decision_type,
                rationale=body.rationale,
                source_run_ids=body.source_run_ids,
                source_execution_ids=body.source_execution_ids,
            ),
        )
        return serialize(decision)
    except PlatformServiceError as exc:
        raise_platform_error(exc)

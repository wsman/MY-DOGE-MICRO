"""v1 project routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from doge.interfaces.api import deps
from doge.interfaces.api.handlers import ProjectHandler
from doge.interfaces.gateway.routers._common import serialize
from doge.interfaces.gateway.routers._platform_common import (
    build_project_service,
    platform_context,
    raise_platform_error,
    require_platform_objects,
)
from doge.platform.workspace import PlatformServiceError, ProjectService

router = APIRouter(dependencies=[Depends(deps.require_api_token)])


class ProjectCreate(BaseModel):
    workspace_id: str
    name: str = Field(min_length=1, max_length=160)
    description: str = ""
    default_market: str | None = None


@router.get("/projects", dependencies=[Depends(require_platform_objects)])
async def list_projects(
    request: Request,
    workspace_id: str | None = None,
    limit: int = 100,
    service: ProjectService = Depends(build_project_service),
):
    try:
        items = ProjectHandler(service=service).list(
            context=platform_context(request),
            workspace_id=workspace_id,
            limit=limit,
        )
        return {"projects": serialize(items)}
    except PlatformServiceError as exc:
        raise_platform_error(exc)


@router.post("/projects", dependencies=[Depends(require_platform_objects)], status_code=201)
async def create_project(
    request: Request,
    body: ProjectCreate,
    service: ProjectService = Depends(build_project_service),
):
    try:
        project = ProjectHandler(service=service).create(
            context=platform_context(request),
            workspace_id=body.workspace_id,
            name=body.name,
            description=body.description,
            default_market=body.default_market,
        )
        return serialize(project)
    except PlatformServiceError as exc:
        raise_platform_error(exc)


@router.get("/projects/{project_id}", dependencies=[Depends(require_platform_objects)])
async def get_project(
    request: Request,
    project_id: str,
    service: ProjectService = Depends(build_project_service),
):
    try:
        project = ProjectHandler(service=service).get(
            context=platform_context(request),
            project_id=project_id,
        )
        return serialize(project)
    except PlatformServiceError as exc:
        raise_platform_error(exc)

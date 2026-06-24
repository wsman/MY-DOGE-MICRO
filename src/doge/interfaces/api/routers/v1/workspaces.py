"""v1 workspace routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from doge.interfaces.api import deps
from doge.interfaces.api.routers.v1._common import serialize
from doge.interfaces.api.routers.v1._platform_common import (
    build_workspace_service,
    platform_context,
    raise_platform_error,
    require_platform_objects,
)
from doge.platform.workspace import PlatformServiceError, WorkspaceService

router = APIRouter(dependencies=[Depends(deps.require_api_token)])


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""


@router.get("/workspaces", dependencies=[Depends(require_platform_objects)])
async def list_workspaces(
    request: Request,
    limit: int = 100,
    service: WorkspaceService = Depends(build_workspace_service),
):
    try:
        items = service.list(platform_context(request), limit=limit)
        return {"workspaces": serialize(items)}
    except PlatformServiceError as exc:
        raise_platform_error(exc)


@router.post("/workspaces", dependencies=[Depends(require_platform_objects)], status_code=201)
async def create_workspace(
    request: Request,
    body: WorkspaceCreate,
    service: WorkspaceService = Depends(build_workspace_service),
):
    try:
        workspace = service.create(platform_context(request), name=body.name, description=body.description)
        return serialize(workspace)
    except PlatformServiceError as exc:
        raise_platform_error(exc)


@router.get("/workspaces/{workspace_id}", dependencies=[Depends(require_platform_objects)])
async def get_workspace(
    request: Request,
    workspace_id: str,
    service: WorkspaceService = Depends(build_workspace_service),
):
    try:
        return serialize(service.get(platform_context(request), workspace_id))
    except PlatformServiceError as exc:
        raise_platform_error(exc)

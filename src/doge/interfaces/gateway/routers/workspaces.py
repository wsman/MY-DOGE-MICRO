"""v1 workspace routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from doge.interfaces.api import deps
from doge.interfaces.api.handlers import WorkspaceHandler
from doge.interfaces.gateway.routers._common import serialize
from doge.interfaces.gateway.routers._response_models import (
    WorkspaceListResponse,
    WorkspaceResponse,
)
from doge.interfaces.gateway.routers._platform_common import (
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


@router.get(
    "/workspaces",
    response_model=WorkspaceListResponse,
    dependencies=[Depends(require_platform_objects)],
)
async def list_workspaces(
    request: Request,
    limit: int = 100,
    service: WorkspaceService = Depends(build_workspace_service),
):
    try:
        items = WorkspaceHandler(service=service).list(context=platform_context(request), limit=limit)
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
        workspace = WorkspaceHandler(service=service).create(
            context=platform_context(request),
            name=body.name,
            description=body.description,
        )
        return serialize(workspace)
    except PlatformServiceError as exc:
        raise_platform_error(exc)


@router.get(
    "/workspaces/{workspace_id}",
    response_model=WorkspaceResponse,
    dependencies=[Depends(require_platform_objects)],
)
async def get_workspace(
    request: Request,
    workspace_id: str,
    service: WorkspaceService = Depends(build_workspace_service),
):
    try:
        workspace = WorkspaceHandler(service=service).get(
            context=platform_context(request),
            workspace_id=workspace_id,
        )
        return serialize(workspace)
    except PlatformServiceError as exc:
        raise_platform_error(exc)

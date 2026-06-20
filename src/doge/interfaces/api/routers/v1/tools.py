"""v1 tool registry routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from doge.application.agent.tools import build_default_tool_registry
from doge.interfaces.api import deps

router = APIRouter(dependencies=[Depends(deps.require_api_token)])


@router.get("/tools")
async def list_tools():
    return {"tools": build_default_tool_registry().schemas}

"""v1 tool registry routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from doge.core.ports.enterprise_governance import IEnterpriseGovernanceRepository
from doge.interfaces.api import deps
from doge.interfaces.api.enterprise_access import append_audit, tool_allowed

router = APIRouter(dependencies=[Depends(deps.require_api_token)])


@router.get("/tools")
async def list_tools(
    request: Request,
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    registry = deps.get_app_container().runtime.build_default_tool_registry()
    tools = [
        schema
        for schema in registry.schemas
        if tool_allowed(
            request,
            governance,
            schema.get("function", {}).get("name", ""),
            schema.get("x-doge-category", ""),
        )
    ]
    append_audit(request, governance, "tool_list", "tool", "*", metadata={"count": len(tools)})
    return {"tools": tools}

"""MCP tool: list_views."""

from doge.application.composition import build_view_service


async def list_views() -> str:
    svc = build_view_service()
    return svc.list_views()

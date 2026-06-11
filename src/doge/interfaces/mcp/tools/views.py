"""MCP tool: list_views."""

from doge.core.services import ViewService
from doge.infrastructure.database.duckdb import DuckDBConnection


async def list_views() -> str:
    svc = ViewService(DuckDBConnection(read_only=True))
    return svc.list_views()

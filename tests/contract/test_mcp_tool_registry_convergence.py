"""Contract: MCP data tools converge on the shared ToolRegistry.

Sprint 020 closed the last architecturally-weighty gap from the strategic
review: the MCP server's six data tools dispatch through the same ToolRegistry
the HTTP gateway uses (``doge.application.tools``), so MCP / runtime / HTTP
share one tool surface. The former hand-rolled ``doge.interfaces.mcp.tools``
wrapper package was removed.

These tests pin the convergence:
  * the six MCP data-tool names are a subset of the registry's tool names
  * the MCP-declared input parameters are a subset of registry schema properties
  * a registry-dispatched ``query_stock`` renders a non-empty table (real rows
    or the deterministic demo fallback)
  * ``list_views`` keeps its JSON-list text contract
"""

import json

import pytest

from doge.interfaces.mcp import server as srv

mcp = srv.create_mcp_server()

MCP_DATA_TOOLS = {
    "query_stock",
    "stock_overview",
    "rsrs_ranking",
    "market_breadth",
    "volume_anomalies",
    "list_views",
}


def _registry_schemas_by_name() -> dict[str, dict]:
    registry = srv._get_data_registry()
    return {schema["function"]["name"]: schema for schema in registry.schemas}


def _registry_names() -> set[str]:
    return set(_registry_schemas_by_name())


def _registry_properties(schema: dict) -> set[str]:
    parameters = schema.get("function", {}).get("parameters", {})
    return set((parameters.get("properties") or {}).keys())


def _mcp_properties(tool) -> set[str]:
    input_schema = getattr(tool, "inputSchema", None) or getattr(tool, "input_schema", None)
    if input_schema is None and hasattr(tool, "model_dump"):
        dumped = tool.model_dump(by_alias=True)
        input_schema = dumped.get("inputSchema") or dumped.get("input_schema")
    return set(((input_schema or {}).get("properties") or {}).keys())


def test_mcp_data_tool_names_are_subset_of_registry():
    """Every MCP data tool must exist in the shared registry."""
    names = _registry_names()
    missing = MCP_DATA_TOOLS - names
    assert not missing, f"MCP data tools missing from registry: {missing}"


@pytest.mark.asyncio
async def test_mcp_data_tool_params_are_subset_of_registry_schema():
    """The curated MCP surface must not invent params outside the registry schema."""
    mcp_tools = {tool.name: tool for tool in await mcp.list_tools()}
    registry_schemas = _registry_schemas_by_name()

    for name in MCP_DATA_TOOLS:
        assert name in mcp_tools, f"MCP data tool missing from MCP surface: {name}"
        mcp_props = _mcp_properties(mcp_tools[name])
        registry_props = _registry_properties(registry_schemas[name])
        extra = mcp_props - registry_props
        assert not extra, f"{name} declares MCP-only params not in registry schema: {extra}"


@pytest.mark.asyncio
async def test_query_stock_dispatch_returns_non_empty_table():
    """The MCP -> registry -> provider -> formatter path must yield data."""
    result = await srv.query_stock("600000", "cn", 5)
    assert isinstance(result, str)
    assert "No data" not in result
    assert len(result.splitlines()) >= 2


@pytest.mark.asyncio
async def test_list_views_dispatch_returns_json_list():
    """list_views keeps its JSON-list text contract through the registry."""
    result = await srv.list_views()
    data = json.loads(result)
    assert isinstance(data, list)
    assert data, "list_views must return a non-empty view list (real or fallback)"

"""Architecture gate: the MCP server converges on the shared ToolRegistry.

Sprint 020 removed the parallel hand-rolled tool surface
(``doge.interfaces.mcp.tools``). This AST guard prevents a regression that
re-introduces wrapper modules or bypasses the canonical registry.
"""

from __future__ import annotations

import ast
from pathlib import Path

SERVER_PATH = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "doge"
    / "interfaces"
    / "mcp"
    / "server.py"
)

EXPECTED_DATA_TOOL_FUNCTIONS = {
    "query_stock",
    "stock_overview",
    "rsrs_ranking",
    "market_breadth",
    "volume_anomalies",
    "list_views",
}


def _import_hits(tree: ast.AST) -> list[tuple[str, str | None]]:
    hits: list[tuple[str, str | None]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                hits.append((node.module, alias.name))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                hits.append((alias.name, None))
    return hits


def test_mcp_server_imports_shared_tool_registry() -> None:
    tree = ast.parse(SERVER_PATH.read_text(encoding="utf-8"))
    hits = _import_hits(tree)

    has_registry_import = any(
        module == "doge.application.tools.factory" and name == "build_default_tool_registry"
        for module, name in hits
    )
    assert has_registry_import, (
        "MCP server must import build_default_tool_registry from "
        "doge.application.tools.factory so data tools share the gateway's registry"
    )

    modules = {module for module, _ in hits}
    assert "doge.interfaces.mcp.tools" not in modules, (
        "MCP server must not import the removed doge.interfaces.mcp.tools wrapper package"
    )


def test_mcp_server_defines_six_data_tool_functions() -> None:
    """The six data tools are defined (registry-backed) in the server module."""
    tree = ast.parse(SERVER_PATH.read_text(encoding="utf-8"))
    defined = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    missing = EXPECTED_DATA_TOOL_FUNCTIONS - defined
    assert not missing, f"MCP server must define the data tool functions: {missing}"

"""Architecture guards for Sprint G runtime/tool/module boundaries."""

from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_runtime_and_tool_layers_do_not_import_transport_or_ui_frameworks() -> None:
    forbidden_prefixes = (
        "fastapi",
        "openai",
        "PyQt6",
        "doge.interfaces",
    )
    for root in [
        PROJECT_ROOT / "src" / "doge" / "application" / "agent",
        PROJECT_ROOT / "src" / "doge" / "application" / "tools",
    ]:
        for path in root.glob("*.py"):
            imports = _imports(path)
            illegal = [
                item
                for item in imports
                if item == "requests" or item == "httpx" or item.startswith(forbidden_prefixes)
            ]
            assert illegal == [], f"{path.relative_to(PROJECT_ROOT)} imports transport/UI concerns: {illegal}"


def test_runtime_gateway_and_tools_do_not_directly_import_legacy_top_level_modules() -> None:
    forbidden_roots = ("macro", "micro", "interface")
    for root in [
        PROJECT_ROOT / "src" / "doge" / "application" / "agent",
        PROJECT_ROOT / "src" / "doge" / "application" / "tools",
        PROJECT_ROOT / "src" / "doge" / "interfaces" / "gateway",
    ]:
        for path in root.rglob("*.py"):
            imports = _imports(path)
            illegal = [
                item
                for item in imports
                if item == "interface" or item.startswith(tuple(f"{root_name}." for root_name in forbidden_roots))
            ]
            assert illegal == [], f"{path.relative_to(PROJECT_ROOT)} imports legacy modules directly: {illegal}"


def test_application_agent_tools_module_remains_a_compatibility_shim() -> None:
    path = PROJECT_ROOT / "src" / "doge" / "application" / "agent" / "tools.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    body = _without_module_docstring(tree.body)

    assert all(isinstance(node, (ast.ImportFrom, ast.Assign)) for node in body)
    assert "from doge.application.tools import ToolRegistry, ToolResult, build_default_tool_registry" in path.read_text(
        encoding="utf-8"
    )
    assert "def " not in path.read_text(encoding="utf-8")
    assert "class " not in path.read_text(encoding="utf-8")


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def _without_module_docstring(nodes: list[ast.stmt]) -> list[ast.stmt]:
    if nodes and isinstance(nodes[0], ast.Expr) and isinstance(nodes[0].value, ast.Constant):
        if isinstance(nodes[0].value.value, str):
            return nodes[1:]
    return nodes

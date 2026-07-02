"""Sprint E import gates for new bounded-context packages."""

from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DOGE = PROJECT_ROOT / "src" / "doge"


def test_new_platform_and_product_code_does_not_import_application_composition() -> None:
    violations = []
    for root in [SRC_DOGE / "platform", SRC_DOGE / "products"]:
        for path, imported in _imports_under(root):
            if imported == "doge.application.composition":
                violations.append(f"{path.relative_to(PROJECT_ROOT)} imports {imported}")

    assert violations == []


def test_tool_application_service_uses_context_owned_tool_facades() -> None:
    path = SRC_DOGE / "application" / "tools" / "registry_factory.py"
    imports = set(_module_imports(path))

    assert {
        "doge.platform.governance.tools",
        "doge.products.market.tools",
        "doge.products.portfolio.tools",
        "doge.products.quant.tools",
        "doge.products.research.tools",
    }.issubset(imports)
    assert "doge.application.capabilities.market_provider" not in imports
    assert "doge.application.capabilities.research_provider" not in imports
    assert "doge.application.capabilities.portfolio_provider" not in imports
    assert "doge.application.capabilities.quant_provider" not in imports


def test_tool_application_service_facade_does_not_import_provider_owners() -> None:
    path = SRC_DOGE / "application" / "agent" / "tool_service.py"
    imports = set(_module_imports(path))

    assert "doge.platform.governance.tools" not in imports
    assert "doge.products.market.tools" not in imports
    assert "doge.products.portfolio.tools" not in imports
    assert "doge.products.quant.tools" not in imports
    assert "doge.products.research.tools" not in imports
    assert "doge.application.capabilities.market_provider" not in imports
    assert "doge.application.capabilities.research_provider" not in imports
    assert "doge.application.capabilities.portfolio_provider" not in imports
    assert "doge.application.capabilities.quant_provider" not in imports


def _imports_under(root: Path) -> list[tuple[Path, str]]:
    imports: list[tuple[Path, str]] = []
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        for imported in _module_imports(path):
            imports.append((path, imported))
    return imports


def _module_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports

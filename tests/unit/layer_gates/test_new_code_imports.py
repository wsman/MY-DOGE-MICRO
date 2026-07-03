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


# Interface-layer facade-adoption ratchet (Sprint 019). ------------------------
# Interface layers must import platform/product facades, not doge.application.*
# internals. The frozen grandfather set is shrink-only: the two remaining
# imports have no platform/product facade home in this sprint.
INTERFACE_FACADE_SCAN_DIRS = (
    SRC_DOGE / "interfaces" / "gateway" / "routers",
    SRC_DOGE / "interfaces" / "api" / "handlers",
    SRC_DOGE / "interfaces" / "cli" / "commands",
)
INTERFACE_FACADE_SCAN_FILES = (
    SRC_DOGE / "interfaces" / "api" / "enterprise_access.py",
    SRC_DOGE / "interfaces" / "api" / "factories.py",
)
INTERFACE_GRANDFATHERED = frozenset(
    {
        ("src/doge/interfaces/api/handlers/sessions.py", "doge.application.use_cases.session_use_cases"),
        ("src/doge/interfaces/cli/commands/macro.py", "doge.application.contracts.request"),
    }
)


def test_interface_layers_use_platform_facades() -> None:
    """Ratchet: interface layers import facades, not doge.application.* internals.

    Scanned: gateway routers, api handlers, cli commands, plus the two api
    factory/access files. ``interfaces/api_legacy`` is exempt (frozen compat
    surface under ADR-0024/0027). Any new ``doge.application.*`` import in the
    scanned set fails unless the frozen grandfather allowlist is deliberately
    grown in review.
    """
    paths: list[Path] = []
    for root in INTERFACE_FACADE_SCAN_DIRS:
        paths.extend(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)
    paths.extend(INTERFACE_FACADE_SCAN_FILES)

    findings: list[tuple[str, int, str]] = []  # (rel_path, lineno, module)
    for path in paths:
        rel = path.relative_to(PROJECT_ROOT).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.append(node.module)
            for module in modules:
                if module == "doge.application" or module.startswith("doge.application."):
                    findings.append((rel, node.lineno, module))

    actual = {(rel, module) for rel, _lineno, module in findings}
    extra = actual - INTERFACE_GRANDFATHERED
    missing = INTERFACE_GRANDFATHERED - actual
    if not extra and not missing:
        return

    lines = ["Interface facade-adoption ratchet drift."]
    if extra:
        lines.append("Unexpected doge.application.* imports (migrate to a platform/product facade):")
        for rel, lineno, module in sorted(findings):
            if (rel, module) in extra:
                lines.append(f"  {rel}:{lineno} -> {module}")
    if missing:
        lines.append("Grandfathered imports no longer present (update INTERFACE_GRANDFATHERED):")
        for rel, module in sorted(missing):
            lines.append(f"  {rel} -> {module}")
    raise AssertionError("\n".join(lines))


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

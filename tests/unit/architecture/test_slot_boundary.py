"""Architecture gate: doge.platform.slots stays a pure contract package (ADR-0042).

The slot contract package may import only ``doge.core.*``, ``doge.shared.*``,
``doge.platform.slots.*`` (self) and the standard library. It must not import
``doge.config``, ``doge.infrastructure``, ``doge.adapters``, ``doge.products``,
``doge.application.tools``, ``doge.application.agent``, ``doge.bootstrap`` or
``doge.interfaces`` — and must not import any of the global FORBIDDEN_PREFIXES
from ``scripts/validate_import_boundaries.py``. The boundary validator itself
does not enforce ``platform/slots`` purity (it only checks FORBIDDEN_PREFIXES +
the gateway-routers location rule), so this AST ratchet is the gate.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_SLOT_ROOT = (
    Path(__file__).resolve().parents[3] / "src" / "doge" / "platform" / "slots"
)

_FORBIDDEN_ROOTS = (
    "doge.infrastructure",
    "doge.adapters",
    "doge.products",
    "doge.application.tools",
    "doge.application.agent",
    "doge.bootstrap",
    "doge.interfaces",
    "doge.config",
)

_FORBIDDEN_PREFIXES = (
    "doge.interfaces.api.routers.v1",
    "doge.application.agent.tools",
    "doge.interfaces.api_legacy",
    "doge.infrastructure.agent.inmemory_runtime",
)


def _imported_modules(tree: ast.AST) -> list[str]:
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                modules.append(node.module)
    return modules


def _is_forbidden(module: str) -> bool:
    for forbidden in _FORBIDDEN_ROOTS + _FORBIDDEN_PREFIXES:
        if module == forbidden or module.startswith(forbidden + "."):
            return True
    return False


def _slot_files() -> list[Path]:
    return sorted(p for p in _SLOT_ROOT.rglob("*.py") if "__pycache__" not in p.parts)


def test_slot_package_has_files() -> None:
    files = _slot_files()
    assert files, f"no slot files found under {_SLOT_ROOT}"


@pytest.mark.parametrize("path", _slot_files(), ids=lambda p: p.relative_to(_SLOT_ROOT).as_posix())
def test_slot_module_imports_only_allowed_roots(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    offenders = [m for m in _imported_modules(tree) if _is_forbidden(m)]
    assert not offenders, (
        f"{path.name} imports forbidden module(s) {offenders}; "
        "platform/slots may import only doge.core.*, doge.shared.*, "
        "doge.platform.slots.* and the standard library"
    )

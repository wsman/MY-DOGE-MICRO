"""AST-level dependency gates for bounded-context migration."""

from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DOGE = PROJECT_ROOT / "src" / "doge"


def test_platform_runtime_does_not_import_product_contexts_or_adapters() -> None:
    violations = _forbidden_imports(
        SRC_DOGE / "platform" / "runtime",
        forbidden_roots=("doge.products", "doge.infrastructure", "doge.adapters"),
    )

    assert violations == []


def test_product_contexts_do_not_import_sibling_product_contexts() -> None:
    violations: list[str] = []
    products_root = SRC_DOGE / "products"
    for context_dir in products_root.iterdir():
        if not context_dir.is_dir():
            continue
        forbidden = [
            f"doge.products.{sibling.name}"
            for sibling in products_root.iterdir()
            if sibling.is_dir() and sibling.name != context_dir.name
        ]
        for path, imported in _imports_under(context_dir):
            if any(_matches_import_root(imported, root) for root in forbidden):
                violations.append(f"{path.relative_to(PROJECT_ROOT)} imports {imported}")

    assert violations == []


def test_entrypoints_do_not_import_infrastructure_or_adapter_packages() -> None:
    violations = _forbidden_imports(
        SRC_DOGE / "entrypoints",
        forbidden_roots=("doge.infrastructure", "doge.adapters"),
    )

    assert violations == []


def _forbidden_imports(root: Path, *, forbidden_roots: tuple[str, ...]) -> list[str]:
    violations: list[str] = []
    for path, imported in _imports_under(root):
        if any(_matches_import_root(imported, root) for root in forbidden_roots):
            violations.append(f"{path.relative_to(PROJECT_ROOT)} imports {imported}")
    return violations


def _imports_under(root: Path) -> list[tuple[Path, str]]:
    imports: list[tuple[Path, str]] = []
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend((path, alias.name) for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append((path, node.module))
    return imports


def _matches_import_root(imported: str, root: str) -> bool:
    return imported == root or imported.startswith(f"{root}.")

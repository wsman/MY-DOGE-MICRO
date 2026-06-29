"""Sprint E bounded-context ownership gate."""

from __future__ import annotations

import ast
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
MANIFEST = PROJECT_ROOT / "docs" / "architecture" / "module-ownership.yaml"


def test_module_ownership_manifest_covers_each_file_once() -> None:
    manifest = _load_manifest()
    owned: dict[Path, str] = {}

    for context_name, context in manifest["contexts"].items():
        for pattern in context["path_patterns"]:
            for path in PROJECT_ROOT.glob(pattern):
                if not path.is_file() or path.suffix != ".py":
                    continue
                previous = owned.setdefault(path, context_name)
                assert previous == context_name, (
                    f"{path.relative_to(PROJECT_ROOT)} owned by both {previous} and {context_name}"
                )

    covered_files = {
        path
        for root in manifest["covered_roots"]
        for path in (PROJECT_ROOT / root).rglob("*.py")
        if "__pycache__" not in path.parts
    }

    assert covered_files - set(owned) == set()


def test_module_ownership_forbidden_imports_are_enforced() -> None:
    manifest = _load_manifest()
    violations: list[str] = []

    for context_name, context in manifest["contexts"].items():
        owned_files = {
            path
            for pattern in context["path_patterns"]
            for path in PROJECT_ROOT.glob(pattern)
            if path.is_file() and path.suffix == ".py"
        }
        allowlist = {
            (PROJECT_ROOT / item["path"], item["import"])
            for item in context.get("compatibility_allowlist", [])
        }
        for path in owned_files:
            for imported in _module_imports(path):
                for forbidden in context["forbidden_dependencies"]:
                    if _matches_import_root(imported, forbidden) and (path, forbidden) not in allowlist:
                        violations.append(
                            f"{context_name}: {path.relative_to(PROJECT_ROOT)} imports {imported}"
                        )

    assert violations == []


def _load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _module_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def _matches_import_root(imported: str, root: str) -> bool:
    return imported == root or imported.startswith(f"{root}.")

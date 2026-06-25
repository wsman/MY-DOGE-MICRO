"""Architecture gate for runtime/application dependency direction."""

from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_application_agent_does_not_import_platform_runtime() -> None:
    for path in (PROJECT_ROOT / "src" / "doge" / "application" / "agent").glob("*.py"):
        imports = _imports(path)
        illegal = [item for item in imports if item.startswith("doge.platform.runtime")]
        assert illegal == [], f"{path.name} imports platform runtime: {illegal}"


def test_platform_runtime_services_do_not_import_application_agent() -> None:
    runtime_root = PROJECT_ROOT / "src" / "doge" / "platform" / "runtime"
    for path in runtime_root.glob("*.py"):
        if path.name == "__init__.py":
            continue
        imports = _imports(path)
        illegal = [item for item in imports if item.startswith("doge.application.agent")]
        assert illegal == [], f"{path.name} imports application agent internals: {illegal}"


def test_platform_runtime_facade_documents_application_compat_exports() -> None:
    source = (PROJECT_ROOT / "src" / "doge" / "platform" / "runtime" / "__init__.py").read_text(
        encoding="utf-8"
    )

    assert "Exports are lazy to avoid import cycles" in source
    assert "doge.application.agent.runtime_kernel" in source
    assert "doge.platform.runtime.services" in source


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports

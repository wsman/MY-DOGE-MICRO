"""Architecture guard for platform runtime services as orchestration only."""

from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SERVICES_PATH = PROJECT_ROOT / "src" / "doge" / "platform" / "runtime" / "services.py"


def test_platform_runtime_services_do_not_import_application_agent() -> None:
    imports = _imports(SERVICES_PATH)

    assert [item for item in imports if item.startswith("doge.application.agent")] == []


def test_platform_runtime_services_do_not_import_lifecycle_ownership() -> None:
    source = SERVICES_PATH.read_text(encoding="utf-8")
    imports = set(_imports(SERVICES_PATH))

    for forbidden in [
        "RunStatus",
        "ensure_transition",
        "ApprovalCoordinator",
        "RunLifecycleService",
        "RunStepper",
    ]:
        assert forbidden not in imports
        assert f" {forbidden}" not in source


def test_platform_runtime_services_have_no_private_assembler_or_web_search_stage() -> None:
    source = SERVICES_PATH.read_text(encoding="utf-8")
    private_assembler = "_Model" + "ResponseAssembler"
    private_web_search = "_Web" + "SearchStage"

    assert private_assembler not in source
    assert private_web_search not in source
    assert "class WebSearchStage" not in source
    assert "class ModelResponseAssembler" not in source


def test_model_execution_service_does_not_instantiate_response_assembler() -> None:
    model_execution = _class("ModelExecutionService")

    for node in ast.walk(model_execution):
        if isinstance(node, ast.Call):
            name = _call_name(node.func)
            assert name not in {"ModelResponseAssembler", "_Model" + "ResponseAssembler"}


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
            imports.extend(alias.name for alias in node.names)
    return imports


def _class(name: str) -> ast.ClassDef:
    tree = ast.parse(SERVICES_PATH.read_text(encoding="utf-8"), filename=str(SERVICES_PATH))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    raise AssertionError(f"{name} class not found")


def _call_name(func: ast.expr) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None

"""Contract guard for RuntimeKernel as a thin facade."""

from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
KERNEL_PATH = PROJECT_ROOT / "src" / "doge" / "application" / "agent" / "runtime_kernel.py"

EXPECTED_PUBLIC_METHODS = {
    "create_run",
    "run_to_pause_or_completion",
    "queue_run",
    "step",
    "resolve_approval",
    "cancel_run",
    "finalize_cancelled",
    "record_failure",
    "get_run",
    "list_events",
    "list_runs",
    "list_artifacts",
}


def test_runtime_kernel_public_method_set_is_exact() -> None:
    runtime_kernel = _runtime_kernel_class()

    public_methods = {
        node.name
        for node in runtime_kernel.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        and not node.name.startswith("_")
    }

    assert public_methods == EXPECTED_PUBLIC_METHODS


def test_runtime_kernel_documents_public_contract() -> None:
    runtime_kernel = _runtime_kernel_class()
    docstring = ast.get_docstring(runtime_kernel) or ""

    assert "Kernel delegates; collaborators decide." in docstring
    for method_name in EXPECTED_PUBLIC_METHODS:
        assert f"``{method_name}``" in docstring


def test_runtime_kernel_has_no_state_machine_imports_or_calls() -> None:
    tree = _tree()
    source = KERNEL_PATH.read_text(encoding="utf-8")

    assert "ensure_transition" not in source
    assert "can_transition" not in source
    assert "RunStatus" not in source
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = _call_name(node.func)
            assert name not in {"ensure_transition", "can_transition"}


def test_runtime_kernel_public_methods_only_resolve_args_and_delegate() -> None:
    runtime_kernel = _runtime_kernel_class()

    for method in _public_methods(runtime_kernel):
        for node in ast.walk(method):
            assert not isinstance(node, (ast.For, ast.AsyncFor, ast.While, ast.Try, ast.Raise)), method.name
            assert not _uses_run_status(node), method.name
            assert not _assigns_status(node), method.name

        collaborator_calls = [
            node
            for node in ast.walk(method)
            if isinstance(node, ast.Call) and _is_collaborator_call(node)
        ]
        assert len(collaborator_calls) == 1, method.name


def _tree() -> ast.Module:
    return ast.parse(KERNEL_PATH.read_text(encoding="utf-8"), filename=str(KERNEL_PATH))


def _runtime_kernel_class() -> ast.ClassDef:
    for node in _tree().body:
        if isinstance(node, ast.ClassDef) and node.name == "RuntimeKernel":
            return node
    raise AssertionError("RuntimeKernel class not found")


def _public_methods(runtime_kernel: ast.ClassDef) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    return [
        node
        for node in runtime_kernel.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        and not node.name.startswith("_")
    ]


def _call_name(func: ast.expr) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _is_collaborator_call(node: ast.Call) -> bool:
    func = node.func
    if not isinstance(func, ast.Attribute):
        return False
    owner = func.value
    if not isinstance(owner, ast.Attribute):
        return False
    return isinstance(owner.value, ast.Name) and owner.value.id == "self" and owner.attr in {
        "_lifecycle",
        "_stepper",
        "_approval",
    }


def _uses_run_status(node: ast.AST) -> bool:
    return isinstance(node, ast.Name) and node.id == "RunStatus"


def _assigns_status(node: ast.AST) -> bool:
    if not isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
        return False
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    return any(
        isinstance(target, ast.Attribute) and target.attr == "status"
        for target in targets
    )

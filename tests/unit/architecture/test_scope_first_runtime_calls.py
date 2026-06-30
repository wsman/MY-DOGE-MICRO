"""Architecture guard: runtime calls outside compatibility adapters must be scope-first."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from doge.infrastructure.agent.persisted_runtime import PersistedResearchAgentRuntime
from doge.shared.scope import TenantScope

PROJECT_ROOT = Path(__file__).resolve().parents[3]
_SRC_ROOT = PROJECT_ROOT / "src"
_RUNTIME_ADAPTER_PATH = _SRC_ROOT / "doge" / "infrastructure" / "agent" / "persisted_runtime.py"

_SCOPE_FIRST_RUNTIME_METHODS = {
    "create_run",
    "get_run",
    "run_to_pause_or_completion",
    "queue_run",
    "list_events",
    "list_artifacts",
    "stream_events",
    "resume_run",
    "resolve_approval",
    "resolve_approval_and_resume",
    "cancel_run",
    "finalize_cancelled",
    "record_failure",
}


def _is_runtime_call(node: ast.AST, method_name: str) -> bool:
    """Match calls of the form `runtime.<method_name>(...)` or `<name>.runtime.<method_name>(...)`."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Attribute) and func.attr == method_name:
        if isinstance(func.value, ast.Name) and func.value.id == "runtime":
            return True
        if (
            isinstance(func.value, ast.Attribute)
            and func.value.attr == "runtime"
        ):
            return True
    return False


def _first_arg_is_scope(node: ast.Call) -> bool:
    """Return True if the first positional arg is a TenantScope expression or a `scope` variable."""
    if not node.args:
        return False
    first = node.args[0]
    if isinstance(first, ast.Name) and first.id in ("scope", "resolved_scope", "tenant_scope"):
        return True
    if isinstance(first, ast.Call):
        func = first.func
        if isinstance(func, ast.Name):
            if func.id == "TenantScope":
                return True
            if "scope" in func.id.lower():
                return True
        if isinstance(func, ast.Attribute) and func.attr in (
            "local",
            "enterprise",
            "from_tenant_id",
        ):
            return True
    return False


def _find_unscoped_runtime_calls(source_path: Path) -> list[tuple[int, str, int]]:
    """Return (line, method, arg_count) for unscoped runtime method calls."""
    text = source_path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    offenders: list[tuple[int, str, int]] = []

    for node in ast.walk(tree):
        for method in _SCOPE_FIRST_RUNTIME_METHODS:
            if _is_runtime_call(node, method):
                call = node
                if not _first_arg_is_scope(call):
                    offenders.append((call.lineno, method, len(call.args)))

    return offenders


def _src_python_files() -> list[Path]:
    return sorted(_SRC_ROOT.rglob("*.py"))


def test_persisted_runtime_adapter_still_supports_legacy_signature() -> None:
    """The compatibility adapter must accept both scope-first and legacy forms."""
    import inspect

    source = inspect.getsource(PersistedResearchAgentRuntime)
    for method in _SCOPE_FIRST_RUNTIME_METHODS:
        assert f"async def {method}(" in source or f"def {method}(" in source

    # The adapter uses helper functions that resolve dual signatures.
    assert "_run_args" in source
    assert "_run_execution_args" in source
    assert "_create_run_args" in source


def test_persisted_runtime_adapter_rejects_tenant_mismatch() -> None:
    """Passing both a trusted scope and a conflicting tenant_id must raise."""
    from unittest.mock import MagicMock

    runtime = PersistedResearchAgentRuntime(kernel=MagicMock())
    with pytest.raises(ValueError, match="tenant mismatch"):
        runtime.get_run(TenantScope.enterprise("t1"), "r1", tenant_id="t2")


def test_no_unscoped_runtime_calls_in_production_source() -> None:
    """Production callers outside the compatibility adapter must pass an explicit scope."""
    offenders = []
    for path in _src_python_files():
        if path == _RUNTIME_ADAPTER_PATH:
            continue
        relative = path.relative_to(PROJECT_ROOT).as_posix()
        # Legacy /api/* routes and PyQt/demo surfaces are allowed to use
        # TenantScope.local() explicitly, but not unscoped calls. Tests are
        # excluded from this scan because they exercise compatibility behavior.
        if "/tests/" in relative or relative.startswith("tests/"):
            continue
        for lineno, method, arg_count in _find_unscoped_runtime_calls(path):
            offenders.append(f"{relative}:{lineno} {method}({arg_count} args)")

    assert offenders == [], "unscoped runtime calls found: " + "\n".join(offenders)

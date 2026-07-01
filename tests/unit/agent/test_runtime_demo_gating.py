"""K-5: demo/test runtime adapters must be opt-in, not a silent production fallback.

The scripted-model and in-memory runtime are demo/test-only surfaces. They must
(a) be lazy-imported by the factory module (not loaded at import time) and
(b) be refused outside local-demo mode so enterprise/remote production paths
fail closed instead of silently using a scripted model.
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

from doge.bootstrap.runtime_factories import runtime_kernel


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_KERNEL_PATH = (
    PROJECT_ROOT / "src" / "doge" / "bootstrap" / "runtime_factories" / "runtime_kernel.py"
)
_FORBIDDEN_PREFIXES = (
    "doge.infrastructure.agent.inmemory_runtime",
    "doge.infrastructure.agent.scripted_model",
)


def test_runtime_kernel_does_not_import_demo_adapters_at_module_load() -> None:
    tree = ast.parse(RUNTIME_KERNEL_PATH.read_text(encoding="utf-8"), filename=str(RUNTIME_KERNEL_PATH))
    offenders: list[str] = []
    for node in tree.body:  # module-level statements only (lazy imports live inside functions)
        modules: list[str] = []
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.append(node.module)
        for module in modules:
            if any(module == p or module.startswith(p + ".") for p in _FORBIDDEN_PREFIXES):
                offenders.append(module)
    assert offenders == [], (
        "runtime_kernel must lazy-import the demo/test adapters inside the "
        f"factory functions; found top-level imports: {offenders}"
    )


def test_demo_fallback_allowed_in_local_demo_mode(monkeypatch) -> None:
    monkeypatch.delenv("DOGE_ALLOW_DEMO_RUNTIME", raising=False)
    monkeypatch.setattr(
        runtime_kernel,
        "get_settings",
        lambda: SimpleNamespace(auth=SimpleNamespace(mode="local_demo")),
    )
    assert runtime_kernel._demo_fallback_allowed() is True


def test_demo_fallback_disabled_in_enterprise_mode(monkeypatch) -> None:
    monkeypatch.delenv("DOGE_ALLOW_DEMO_RUNTIME", raising=False)
    monkeypatch.setattr(
        runtime_kernel,
        "get_settings",
        lambda: SimpleNamespace(auth=SimpleNamespace(mode="enterprise")),
    )
    assert runtime_kernel._demo_fallback_allowed() is False


def test_demo_fallback_env_override_forces_allow(monkeypatch) -> None:
    monkeypatch.setenv("DOGE_ALLOW_DEMO_RUNTIME", "1")
    monkeypatch.setattr(
        runtime_kernel,
        "get_settings",
        lambda: SimpleNamespace(auth=SimpleNamespace(mode="enterprise")),
    )
    assert runtime_kernel._demo_fallback_allowed() is True


def test_build_research_agent_runtime_fails_closed_outside_demo(monkeypatch) -> None:
    monkeypatch.setattr(runtime_kernel, "_demo_fallback_allowed", lambda: False)

    def _boom(*args, **kwargs):
        raise AssertionError("gate must fire before gateway_container_fn is called")

    with pytest.raises(RuntimeError, match="demo/test-only"):
        runtime_kernel.build_research_agent_runtime(_boom, _boom)

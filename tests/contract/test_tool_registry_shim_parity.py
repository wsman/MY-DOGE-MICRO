"""Compatibility parity for the legacy agent tool-registry shim."""

from __future__ import annotations


def test_agent_tools_shim_exports_canonical_tool_registry_symbols() -> None:
    from doge.application import tools as canonical
    from doge.application.agent import tools as legacy

    assert legacy.ToolRegistry is canonical.ToolRegistry
    assert legacy.ToolResult is canonical.ToolResult
    assert legacy.build_default_tool_registry is canonical.build_default_tool_registry


def test_composition_tool_registry_factory_matches_runtime_container() -> None:
    from doge.application import composition
    from doge.bootstrap import build_runtime_container

    legacy_registry = composition.build_default_tool_registry()
    canonical_registry = build_runtime_container().build_default_tool_registry()

    legacy_tool_names = [schema["function"]["name"] for schema in legacy_registry.schemas]
    canonical_tool_names = [schema["function"]["name"] for schema in canonical_registry.schemas]
    assert legacy_tool_names == canonical_tool_names

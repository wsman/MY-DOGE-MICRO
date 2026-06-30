"""Tool schema helpers backed by provider-owned descriptors."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from doge.application.agent.tool_service import ToolApplicationService
from doge.core.domain.tool_descriptor import ToolDescriptor


def default_tool_descriptors(service: ToolApplicationService | None = None) -> tuple[ToolDescriptor, ...]:
    """Return the canonical provider-owned tool descriptors."""

    return (service or ToolApplicationService()).tool_descriptors()


def default_tool_schemas(service: ToolApplicationService | None = None) -> list[dict[str, Any]]:
    """Return OpenAI/Kimi-compatible schemas for all default tools."""

    return [descriptor.to_schema() for descriptor in default_tool_descriptors(service)]


def descriptors_for_names(
    names: Iterable[str],
    service: ToolApplicationService | None = None,
) -> tuple[ToolDescriptor, ...]:
    """Return descriptors matching ``names`` while preserving registry order."""

    selected = set(names)
    return tuple(
        descriptor
        for descriptor in default_tool_descriptors(service)
        if descriptor.name in selected
    )


def schemas_for_names(
    names: Iterable[str],
    service: ToolApplicationService | None = None,
) -> list[dict[str, Any]]:
    """Return schemas matching ``names`` while preserving registry order."""

    return [descriptor.to_schema() for descriptor in descriptors_for_names(names, service)]


__all__ = [
    "default_tool_descriptors",
    "default_tool_schemas",
    "descriptors_for_names",
    "schemas_for_names",
]

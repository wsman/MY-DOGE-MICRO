"""Tool registry factory helpers."""

from __future__ import annotations

from typing import Any

from doge.application.agent.tool_service import ToolApplicationService
from doge.application.tools.registry import ToolRegistry
from doge.core.ports.tool_entitlement import IToolEntitlementChecker


def build_default_tool_registry(
    service: ToolApplicationService | None = None,
    *,
    entitlement_checker: IToolEntitlementChecker | None = None,
    context: Any = None,
) -> ToolRegistry:
    registry = ToolRegistry(entitlement_checker=entitlement_checker, context=context)
    service = service or ToolApplicationService()
    registry.include_descriptors(service.tool_descriptors(), service)
    return registry


"""Port for enterprise tool entitlement checks."""

from __future__ import annotations

from typing import Any, Protocol

from doge.core.domain.tool_policy import ToolCategory


class IToolEntitlementChecker(Protocol):
    def can_execute(
        self,
        context: Any,
        tool_name: str,
        category: ToolCategory,
    ) -> bool:
        ...

    def requires_approval(
        self,
        context: Any,
        tool_name: str,
        category: ToolCategory,
    ) -> bool:
        ...

    def redact_schema(
        self,
        context: Any,
        schema: dict[str, Any],
        category: ToolCategory,
    ) -> dict[str, Any] | None:
        ...

"""Local entitlement checker for enterprise tool governance demos."""

from __future__ import annotations

from typing import Any

from doge.core.domain.tool_policy import ToolCategory


class SimpleEntitlementChecker:
    """Conservative enterprise rules with permissive local-demo fallback."""

    _HIGH_RISK_ROLES = {"portfolio_manager", "admin"}

    def can_execute(self, context: Any, tool_name: str, category: ToolCategory) -> bool:
        if category == ToolCategory.FORBIDDEN:
            return False
        if category != ToolCategory.HIGH_RISK:
            return True
        role = getattr(context, "role", None)
        if role is None:
            return True
        return role in self._HIGH_RISK_ROLES

    def requires_approval(self, context: Any, tool_name: str, category: ToolCategory) -> bool:
        return category == ToolCategory.HIGH_RISK

    def redact_schema(self, context: Any, schema: dict[str, Any], category: ToolCategory) -> dict[str, Any] | None:
        if not self.can_execute(context, schema.get("function", {}).get("name", ""), category):
            return None
        return schema

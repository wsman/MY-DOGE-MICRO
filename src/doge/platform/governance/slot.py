"""Built-in governance slot for tool entitlement policy composition."""

from __future__ import annotations

from typing import Any, Iterable

from doge.core.domain.tool_policy import ToolCategory
from doge.platform.slots import (
    SCHEMA_VERSION,
    GovernancePolicyContribution,
    ISlot,
    SlotCompatibility,
    SlotContribution,
    SlotContext,
    SlotHealth,
    SlotManifest,
    SlotPermissions,
    SlotProvides,
    SlotType,
)

_MANIFEST = SlotManifest(
    schema_version=SCHEMA_VERSION,
    id="governance.tool_policy",
    name="Tool Governance Policy",
    version="1.0.0",
    type=SlotType.GOVERNANCE,
    owner="governance-evaluation",
    maturity="experimental",
    description=(
        "Contributes the default tool entitlement and approval policy used by "
        "slot-aware tool registry assembly."
    ),
    entrypoint="doge.platform.governance.slot.ToolGovernancePolicySlot",
    provides=SlotProvides(
        capabilities=("tool_entitlement", "approval_policy"),
        metadata={
            "blocked_categories": ("forbidden",),
            "approval_required_categories": ("high_risk",),
        },
    ),
    permissions=SlotPermissions(risk_level="low"),
    health=SlotHealth(status="experimental"),
    feature_flags=("slot_platform", "slot_governance"),
    compatibility=SlotCompatibility(runtime_min="1"),
)


class ToolGovernancePolicySlot(ISlot):
    """Built-in governance slot for tool registry entitlement checks."""

    def manifest(self) -> SlotManifest:
        return _MANIFEST

    def resolve(self, context: SlotContext) -> SlotContribution:
        return SlotContribution(
            slot_id="governance.tool_policy",
            governance_policies=(
                GovernancePolicyContribution(
                    policy_id="governance.tool_policy.default_entitlement",
                    kind="tool_entitlement",
                    payload={
                        "blocked_categories": ("forbidden",),
                        "approval_required_categories": ("high_risk",),
                    },
                    entitlement_checker_factory=_default_checker_factory,
                ),
            ),
        )


class DefaultToolGovernanceChecker:
    """Default slot-contributed tool policy equivalent to ToolRegistry defaults."""

    def can_execute(self, context: Any, tool_name: str, category: ToolCategory) -> bool:
        return category != ToolCategory.FORBIDDEN

    def requires_approval(self, context: Any, tool_name: str, category: ToolCategory) -> bool:
        return category == ToolCategory.HIGH_RISK

    def redact_schema(
        self,
        context: Any,
        schema: dict[str, Any],
        category: ToolCategory,
    ) -> dict[str, Any] | None:
        if not self.can_execute(context, schema.get("function", {}).get("name", ""), category):
            return None
        return schema


class CompositeToolEntitlementChecker:
    """AND/OR composition for slot-contributed tool entitlement checkers."""

    def __init__(self, checkers: Iterable[Any]) -> None:
        self._checkers = tuple(checkers)
        if not self._checkers:
            raise ValueError("CompositeToolEntitlementChecker requires at least one checker")

    def can_execute(self, context: Any, tool_name: str, category: ToolCategory) -> bool:
        return all(
            checker.can_execute(context, tool_name, category)
            for checker in self._checkers
        )

    def requires_approval(self, context: Any, tool_name: str, category: ToolCategory) -> bool:
        return any(
            checker.requires_approval(context, tool_name, category)
            for checker in self._checkers
        )

    def redact_schema(
        self,
        context: Any,
        schema: dict[str, Any],
        category: ToolCategory,
    ) -> dict[str, Any] | None:
        redacted: dict[str, Any] | None = schema
        for checker in self._checkers:
            if redacted is None:
                return None
            redacted = checker.redact_schema(context, redacted, category)
        return redacted


def _default_checker_factory(context: SlotContext) -> DefaultToolGovernanceChecker:
    return DefaultToolGovernanceChecker()

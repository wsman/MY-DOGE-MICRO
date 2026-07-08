"""``governance.actions`` built-in tool slot (ADR-0059, P1).

Groups approval and publishing action descriptors as tool contributions. This
is separate from ``governance.tool_policy``, which contributes policy rather
than executable tool descriptors.
"""

from __future__ import annotations

from doge.platform.slots import (
    SCHEMA_VERSION,
    ISlot,
    SlotCompatibility,
    SlotConfigurationError,
    SlotContribution,
    SlotContext,
    SlotHealth,
    SlotManifest,
    SlotPermissions,
    SlotProvides,
    SlotType,
)

_GOVERNANCE_ACTION_TOOLS = (
    "request_approval",
    "publish_investment_memo",
)

_MANIFEST = SlotManifest(
    schema_version=SCHEMA_VERSION,
    id="governance.actions",
    name="Governance Actions",
    version="1.0.0",
    type=SlotType.TOOL,
    owner="governance-evaluation",
    maturity="experimental",
    description="Approval request and investment memo publishing action tools.",
    entrypoint="doge.platform.governance.actions_slot.GovernanceActionsSlot",
    provides=SlotProvides(
        tools=_GOVERNANCE_ACTION_TOOLS,
        metadata={
            "implementation_grouping": (
                "request_approval is implemented by ComplianceToolProvider; "
                "publish_investment_memo is implemented by PublishingToolProvider "
                "and grouped here as a governed action. No provider code was moved."
            ),
        },
    ),
    permissions=SlotPermissions(database="none", risk_level="medium"),
    health=SlotHealth(status="experimental"),
    feature_flags=("slot_platform",),
    compatibility=SlotCompatibility(runtime_min="1"),
)


class GovernanceActionsSlot(ISlot):
    """Built-in tool slot wrapping governed action descriptors."""

    def manifest(self) -> SlotManifest:
        return _MANIFEST

    def resolve(self, context: SlotContext) -> SlotContribution:
        service = context.tool_application_service
        if service is None:
            raise SlotConfigurationError(
                "governance.actions requires tool_application_service"
            )
        by_name = {
            descriptor.name: descriptor for descriptor in service.tool_descriptors()
        }
        missing = tuple(name for name in _GOVERNANCE_ACTION_TOOLS if name not in by_name)
        if missing:
            raise SlotConfigurationError(
                "governance.actions missing declared tool descriptor(s): "
                + ", ".join(missing)
            )
        tools = tuple(by_name[name] for name in _GOVERNANCE_ACTION_TOOLS)
        return SlotContribution(
            slot_id="governance.actions",
            tools=tools,
            executor=service,
        )

"""``compliance.screening`` built-in tool slot (ADR-0059, P1)."""

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

_COMPLIANCE_SCREENING_TOOLS = ("screen_compliance_risk",)

_MANIFEST = SlotManifest(
    schema_version=SCHEMA_VERSION,
    id="compliance.screening",
    name="Compliance Screening",
    version="1.0.0",
    type=SlotType.TOOL,
    owner="governance-evaluation",
    maturity="experimental",
    description="Compliance risk screening tool grouped as a discoverable slot.",
    entrypoint="doge.platform.governance.compliance_slot.ComplianceScreeningSlot",
    provides=SlotProvides(tools=_COMPLIANCE_SCREENING_TOOLS),
    permissions=SlotPermissions(database="read", risk_level="low"),
    health=SlotHealth(status="experimental"),
    feature_flags=("slot_platform",),
    compatibility=SlotCompatibility(runtime_min="1"),
)


class ComplianceScreeningSlot(ISlot):
    """Built-in tool slot wrapping the compliance screening descriptor."""

    def manifest(self) -> SlotManifest:
        return _MANIFEST

    def resolve(self, context: SlotContext) -> SlotContribution:
        service = context.tool_application_service
        if service is None:
            raise SlotConfigurationError(
                "compliance.screening requires tool_application_service"
            )
        by_name = {
            descriptor.name: descriptor for descriptor in service.tool_descriptors()
        }
        missing = tuple(
            name for name in _COMPLIANCE_SCREENING_TOOLS if name not in by_name
        )
        if missing:
            raise SlotConfigurationError(
                "compliance.screening missing declared tool descriptor(s): "
                + ", ".join(missing)
            )
        tools = tuple(by_name[name] for name in _COMPLIANCE_SCREENING_TOOLS)
        return SlotContribution(
            slot_id="compliance.screening",
            tools=tools,
            executor=service,
        )

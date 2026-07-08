"""``quant.lab`` built-in tool slot (ADR-0059, P1).

Groups the existing bounded SQL descriptor under a quant-lab tool slot while
leaving high-risk Python execution behind its separate facade/feature gate.
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

_QUANT_LAB_TOOLS = ("run_sql_query",)

_MANIFEST = SlotManifest(
    schema_version=SCHEMA_VERSION,
    id="quant.lab",
    name="Quant Lab",
    version="1.0.0",
    type=SlotType.TOOL,
    owner="quant-data-lab",
    maturity="experimental",
    description="Read-only SQL analysis tool grouped as a quant lab slot.",
    entrypoint="doge.products.quant.slot.QuantLabSlot",
    provides=SlotProvides(
        tools=_QUANT_LAB_TOOLS,
        metadata={
            "python_analysis_deferred": (
                "run_python_analysis remains outside this slot because it is "
                "high-risk and separately gated by the Python analysis executor."
            ),
        },
    ),
    permissions=SlotPermissions(database="read", risk_level="low"),
    health=SlotHealth(status="experimental"),
    feature_flags=("slot_platform",),
    compatibility=SlotCompatibility(runtime_min="1"),
)


class QuantLabSlot(ISlot):
    """Built-in tool slot wrapping the canonical quant SQL descriptor."""

    def manifest(self) -> SlotManifest:
        return _MANIFEST

    def resolve(self, context: SlotContext) -> SlotContribution:
        service = context.tool_application_service
        if service is None:
            raise SlotConfigurationError("quant.lab requires tool_application_service")
        by_name = {
            descriptor.name: descriptor for descriptor in service.tool_descriptors()
        }
        missing = tuple(name for name in _QUANT_LAB_TOOLS if name not in by_name)
        if missing:
            raise SlotConfigurationError(
                "quant.lab missing declared tool descriptor(s): "
                + ", ".join(missing)
            )
        tools = tuple(by_name[name] for name in _QUANT_LAB_TOOLS)
        return SlotContribution(slot_id="quant.lab", tools=tools, executor=service)

"""``evidence.core`` built-in tool slot (ADR-0059, P1).

Groups existing research evidence and fundamental-data tool descriptors under a
single discoverable slot. The slot reuses ``ToolApplicationService`` as the
executor and does not move provider code.
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

_EVIDENCE_CORE_TOOLS = (
    "validate_financial_claims",
    "generate_industry_report",
    "lookup_evidence",
    "get_financial_statements",
    "get_company_announcements",
    "calculate_financial_ratios",
    "compare_consensus_estimates",
    "get_industry_classification",
)

_MANIFEST = SlotManifest(
    schema_version=SCHEMA_VERSION,
    id="evidence.core",
    name="Evidence Core",
    version="1.0.0",
    type=SlotType.TOOL,
    owner="research-evidence",
    maturity="experimental",
    description=(
        "Research evidence lookup, claim validation, report generation, and "
        "fundamental data tools grouped as a single discoverable slot."
    ),
    entrypoint="doge.products.research.slot.EvidenceCoreSlot",
    provides=SlotProvides(
        tools=_EVIDENCE_CORE_TOOLS,
        metadata={
            "implementation_grouping": (
                "validate_financial_claims, generate_industry_report, and "
                "lookup_evidence are implemented by ResearchToolProvider; "
                "financial statement, announcement, ratio, consensus, and "
                "classification tools are implemented by FundamentalToolProvider. "
                "No provider code was moved."
            ),
        },
    ),
    permissions=SlotPermissions(database="read", risk_level="low"),
    health=SlotHealth(status="experimental"),
    feature_flags=("slot_platform",),
    compatibility=SlotCompatibility(runtime_min="1"),
)


class EvidenceCoreSlot(ISlot):
    """Built-in tool slot wrapping canonical research evidence descriptors."""

    def manifest(self) -> SlotManifest:
        return _MANIFEST

    def resolve(self, context: SlotContext) -> SlotContribution:
        service = context.tool_application_service
        if service is None:
            raise SlotConfigurationError("evidence.core requires tool_application_service")
        by_name = {
            descriptor.name: descriptor for descriptor in service.tool_descriptors()
        }
        missing = tuple(name for name in _EVIDENCE_CORE_TOOLS if name not in by_name)
        if missing:
            raise SlotConfigurationError(
                "evidence.core missing declared tool descriptor(s): "
                + ", ".join(missing)
            )
        tools = tuple(by_name[name] for name in _EVIDENCE_CORE_TOOLS)
        return SlotContribution(slot_id="evidence.core", tools=tools, executor=service)

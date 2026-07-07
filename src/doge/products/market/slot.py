"""``market.core`` built-in tool slot (ADR-0042, Sprint 033).

Wraps the EXISTING market/quant tool descriptors exposed by
``ToolApplicationService.tool_descriptors()`` and re-uses that same service as
the executor. This slot does not re-implement tools and does not move
``list_views`` (which remains implemented by ``doge.products.quant.tools``); it
only groups the six market-facing tool descriptors under one discoverable slot
manifest.
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

# The six market-facing tool method names contributed by this slot. Declared
# order is stable and mirrored by ``resolve``.
_MARKET_CORE_TOOLS = (
    "query_stock",
    "stock_overview",
    "rsrs_ranking",
    "market_breadth",
    "volume_anomalies",
    "list_views",
)

_MANIFEST = SlotManifest(
    schema_version=SCHEMA_VERSION,
    id="market.core",
    name="Market Core",
    version="1.0.0",
    type=SlotType.TOOL,
    owner="market-intelligence",
    maturity="experimental",
    description=(
        "Ticker lookup, market breadth, RSRS momentum ranking, and volume "
        "anomaly tools grouped as a single discoverable slot."
    ),
    entrypoint="doge.products.market.slot.MarketCoreSlot",
    provides=SlotProvides(
        tools=_MARKET_CORE_TOOLS,
        metadata={
            "list_views_grouping": (
                "list_views is contributed by the quant bounded context "
                "(doge.products.quant.tools) and grouped under market.core for "
                "slot discovery; no code was moved."
            ),
        },
    ),
    permissions=SlotPermissions(database="read", risk_level="low"),
    health=SlotHealth(status="experimental"),
    feature_flags=("slot_platform",),
    compatibility=SlotCompatibility(runtime_min="1"),
)


class MarketCoreSlot(ISlot):
    """Built-in tool slot wrapping the canonical market/quant tool descriptors."""

    def manifest(self) -> SlotManifest:
        return _MANIFEST

    def resolve(self, context: SlotContext) -> SlotContribution:
        service = context.tool_application_service
        if service is None:
            raise SlotConfigurationError("market.core requires tool_application_service")
        by_name = {
            descriptor.name: descriptor for descriptor in service.tool_descriptors()
        }
        missing = tuple(name for name in _MARKET_CORE_TOOLS if name not in by_name)
        if missing:
            raise SlotConfigurationError(
                "market.core missing declared tool descriptor(s): "
                + ", ".join(missing)
            )
        tools = tuple(by_name[name] for name in _MARKET_CORE_TOOLS)
        return SlotContribution(slot_id="market.core", tools=tools, executor=service)

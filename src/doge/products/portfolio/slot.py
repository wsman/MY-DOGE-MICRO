"""``portfolio.core`` built-in tool slot (ADR-0059, P1).

Wraps the existing portfolio-facing tool descriptors exposed by
``ToolApplicationService.tool_descriptors()`` and re-uses that same service as
the executor. No provider code is moved.
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

_PORTFOLIO_CORE_TOOLS = (
    "get_portfolio_exposure",
    "portfolio_risk",
    "scenario_analysis",
    "propose_portfolio_rebalance",
)

_MANIFEST = SlotManifest(
    schema_version=SCHEMA_VERSION,
    id="portfolio.core",
    name="Portfolio Core",
    version="1.0.0",
    type=SlotType.TOOL,
    owner="portfolio-risk",
    maturity="experimental",
    description=(
        "Portfolio exposure, risk, scenario, and rebalance proposal tools "
        "grouped as a single discoverable slot."
    ),
    entrypoint="doge.products.portfolio.slot.PortfolioCoreSlot",
    provides=SlotProvides(
        tools=_PORTFOLIO_CORE_TOOLS,
        metadata={
            "implementation_grouping": (
                "get_portfolio_exposure, portfolio_risk, and scenario_analysis "
                "are implemented by PortfolioToolProvider; "
                "propose_portfolio_rebalance is implemented by "
                "PublishingToolProvider and grouped here by product ownership. "
                "No provider code was moved."
            ),
        },
    ),
    permissions=SlotPermissions(database="read", risk_level="low"),
    health=SlotHealth(status="experimental"),
    feature_flags=("slot_platform",),
    compatibility=SlotCompatibility(runtime_min="1"),
)


class PortfolioCoreSlot(ISlot):
    """Built-in tool slot wrapping canonical portfolio tool descriptors."""

    def manifest(self) -> SlotManifest:
        return _MANIFEST

    def resolve(self, context: SlotContext) -> SlotContribution:
        service = context.tool_application_service
        if service is None:
            raise SlotConfigurationError("portfolio.core requires tool_application_service")
        by_name = {
            descriptor.name: descriptor for descriptor in service.tool_descriptors()
        }
        missing = tuple(name for name in _PORTFOLIO_CORE_TOOLS if name not in by_name)
        if missing:
            raise SlotConfigurationError(
                "portfolio.core missing declared tool descriptor(s): "
                + ", ".join(missing)
            )
        tools = tuple(by_name[name] for name in _PORTFOLIO_CORE_TOOLS)
        return SlotContribution(slot_id="portfolio.core", tools=tools, executor=service)

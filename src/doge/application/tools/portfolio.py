"""Portfolio and risk tool facade exports."""

from __future__ import annotations

from doge.application.tools.schemas import descriptors_for_names, schemas_for_names
from doge.products.portfolio.tools import PortfolioToolProvider

PORTFOLIO_TOOL_NAMES = (
    "get_portfolio_exposure",
    "portfolio_risk",
    "scenario_analysis",
    "propose_portfolio_rebalance",
)


def portfolio_tool_descriptors():
    return descriptors_for_names(PORTFOLIO_TOOL_NAMES)


def portfolio_tool_schemas():
    return schemas_for_names(PORTFOLIO_TOOL_NAMES)


__all__ = [
    "PORTFOLIO_TOOL_NAMES",
    "PortfolioToolProvider",
    "portfolio_tool_descriptors",
    "portfolio_tool_schemas",
]

"""Market tool facade exports."""

from __future__ import annotations

from doge.application.tools.schemas import descriptors_for_names, schemas_for_names
from doge.products.market.tools import MarketToolProvider

MARKET_TOOL_NAMES = (
    "query_stock",
    "stock_overview",
    "rsrs_ranking",
    "market_breadth",
    "volume_anomalies",
)


def market_tool_descriptors():
    return descriptors_for_names(MARKET_TOOL_NAMES)


def market_tool_schemas():
    return schemas_for_names(MARKET_TOOL_NAMES)


__all__ = [
    "MARKET_TOOL_NAMES",
    "MarketToolProvider",
    "market_tool_descriptors",
    "market_tool_schemas",
]

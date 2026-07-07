"""Built-in data source slots for market-data adapters."""

from __future__ import annotations

from doge.infrastructure.data_source.tdx import TDXDataSource
from doge.infrastructure.data_source.yfinance import YFinanceDataSource
from doge.platform.slots import (
    SCHEMA_VERSION,
    DataSourceContribution,
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

_TDX_MANIFEST = SlotManifest(
    schema_version=SCHEMA_VERSION,
    id="data.tdx",
    name="TDX Market Data",
    version="1.0.0",
    type=SlotType.DATA,
    owner="market-intelligence",
    maturity="experimental",
    description="Contributes the TDX market data source adapter.",
    entrypoint="doge.infrastructure.data_source.slot.TDXDataSourceSlot",
    provides=SlotProvides(
        capabilities=("market_data.ohlcv", "market_data.tdx"),
        metadata={"source_id": "data.tdx", "markets": ("cn", "us")},
    ),
    permissions=SlotPermissions(network="allow", risk_level="medium"),
    health=SlotHealth(status="experimental"),
    feature_flags=("slot_platform",),
    compatibility=SlotCompatibility(runtime_min="1"),
)

_YFINANCE_MANIFEST = SlotManifest(
    schema_version=SCHEMA_VERSION,
    id="data.yfinance",
    name="YFinance Market Data",
    version="1.0.0",
    type=SlotType.DATA,
    owner="market-intelligence",
    maturity="experimental",
    description="Contributes the yfinance market data source adapter.",
    entrypoint="doge.infrastructure.data_source.slot.YFinanceDataSourceSlot",
    provides=SlotProvides(
        capabilities=("market_data.ohlcv", "market_data.yfinance"),
        metadata={"source_id": "data.yfinance", "markets": ("cn", "us")},
    ),
    permissions=SlotPermissions(network="allow", risk_level="medium"),
    health=SlotHealth(status="experimental"),
    feature_flags=("slot_platform",),
    compatibility=SlotCompatibility(runtime_min="1"),
)


class TDXDataSourceSlot(ISlot):
    """Built-in data slot wrapping ``TDXDataSource``."""

    def manifest(self) -> SlotManifest:
        return _TDX_MANIFEST

    def resolve(self, context: SlotContext) -> SlotContribution:
        return SlotContribution(
            slot_id="data.tdx",
            data_sources=(
                DataSourceContribution(
                    source_id="data.tdx",
                    factory=_tdx_factory,
                    markets=("cn", "us"),
                    capabilities=("market_data.ohlcv",),
                ),
            ),
        )


class YFinanceDataSourceSlot(ISlot):
    """Built-in data slot wrapping ``YFinanceDataSource``."""

    def manifest(self) -> SlotManifest:
        return _YFINANCE_MANIFEST

    def resolve(self, context: SlotContext) -> SlotContribution:
        return SlotContribution(
            slot_id="data.yfinance",
            data_sources=(
                DataSourceContribution(
                    source_id="data.yfinance",
                    factory=_yfinance_factory,
                    markets=("cn", "us"),
                    capabilities=("market_data.ohlcv",),
                ),
            ),
        )


def _tdx_factory(context: SlotContext) -> TDXDataSource:
    return TDXDataSource()


def _yfinance_factory(context: SlotContext) -> YFinanceDataSource:
    return YFinanceDataSource()

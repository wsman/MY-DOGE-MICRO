"""Built-in data slot tests for Sprint 040."""

from __future__ import annotations

from doge.infrastructure.data_source.slot import TDXDataSourceSlot, YFinanceDataSourceSlot
from doge.infrastructure.data_source.tdx import TDXDataSource
from doge.infrastructure.data_source.yfinance import YFinanceDataSource
from doge.platform.slots import SlotContext, SlotType


def test_tdx_data_source_slot_manifest() -> None:
    manifest = TDXDataSourceSlot().manifest()

    assert manifest.id == "data.tdx"
    assert manifest.type is SlotType.DATA
    assert manifest.owner == "market-intelligence"
    assert manifest.feature_flags == ("slot_platform",)
    assert manifest.provides.capabilities == ("market_data.ohlcv", "market_data.tdx")
    assert manifest.provides.metadata["source_id"] == "data.tdx"
    assert manifest.provides.metadata["markets"] == ("cn", "us")
    assert manifest.permissions.network == "allow"
    assert manifest.permissions.risk_level == "medium"


def test_tdx_data_source_slot_contributes_source() -> None:
    context = SlotContext(settings=object(), feature_flags={"slot_platform": True})

    contribution = TDXDataSourceSlot().resolve(context)

    assert contribution.slot_id == "data.tdx"
    assert len(contribution.data_sources) == 1
    data_source = contribution.data_sources[0]
    assert data_source.source_id == "data.tdx"
    assert data_source.markets == ("cn", "us")
    assert data_source.capabilities == ("market_data.ohlcv",)
    assert isinstance(data_source.factory(context), TDXDataSource)


def test_yfinance_data_source_slot_manifest() -> None:
    manifest = YFinanceDataSourceSlot().manifest()

    assert manifest.id == "data.yfinance"
    assert manifest.type is SlotType.DATA
    assert manifest.owner == "market-intelligence"
    assert manifest.feature_flags == ("slot_platform",)
    assert manifest.provides.capabilities == (
        "market_data.ohlcv",
        "market_data.yfinance",
    )
    assert manifest.provides.metadata["source_id"] == "data.yfinance"
    assert manifest.provides.metadata["markets"] == ("cn", "us")
    assert manifest.permissions.network == "allow"
    assert manifest.permissions.risk_level == "medium"


def test_yfinance_data_source_slot_contributes_source() -> None:
    context = SlotContext(settings=object(), feature_flags={"slot_platform": True})

    contribution = YFinanceDataSourceSlot().resolve(context)

    assert contribution.slot_id == "data.yfinance"
    assert len(contribution.data_sources) == 1
    data_source = contribution.data_sources[0]
    assert data_source.source_id == "data.yfinance"
    assert data_source.markets == ("cn", "us")
    assert data_source.capabilities == ("market_data.ohlcv",)
    assert isinstance(data_source.factory(context), YFinanceDataSource)

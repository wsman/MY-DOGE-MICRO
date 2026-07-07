"""Market data-source registry tests for Sprint 040."""

from __future__ import annotations

import pandas as pd
import pytest

from doge.platform.slots import DataSourceContribution, SlotConfigurationError, SlotContext
from doge.products.market.data_sources import DataSourceRegistry


class _Source:
    def __init__(self, source_id: str) -> None:
        self.source_id = source_id
        self.connected = False
        self.connected_markets: list[str] = []
        self.downloads: list[tuple[str, str, int, int]] = []

    def connect(self, market: str = "cn") -> None:
        self.connected = True
        self.connected_markets.append(market)

    def disconnect(self) -> None:
        self.connected = False

    def is_connected(self) -> bool:
        return self.connected

    def download_kline(
        self,
        ticker: str,
        market: str,
        start: int = 0,
        count: int = 800,
    ) -> pd.DataFrame:
        self.downloads.append((ticker, market, start, count))
        return pd.DataFrame(
            [
                {
                    "date": "2026-07-07",
                    "open": 1.0,
                    "high": 1.0,
                    "low": 1.0,
                    "close": 1.0,
                    "volume": 100,
                    "amount": 100.0,
                }
            ]
        )

    def get_latest_market_date(self, market: str) -> str:
        return f"{market}:2026-07-07"


class _NoArgConnectSource(_Source):
    def connect(self) -> None:  # type: ignore[override]
        self.connected = True
        self.connected_markets.append("<none>")


class _KeywordConnectSource(_Source):
    def connect(self, *, market: str = "cn") -> None:  # type: ignore[override]
        self.connected = True
        self.connected_markets.append(market)


def test_data_source_registry_uses_first_matching_source_by_default() -> None:
    tdx = _Source("data.tdx")
    yfinance = _Source("data.yfinance")
    registry = DataSourceRegistry(
        (
            _contribution("data.tdx", tdx, ("cn", "us")),
            _contribution("data.yfinance", yfinance, ("cn", "us")),
        ),
        _context(),
    )

    registry.connect("cn")
    frame = registry.download_kline("000001.SZ", "cn", start=2, count=3)

    assert registry.source_ids == ("data.tdx", "data.yfinance")
    assert registry.is_connected() is True
    assert tdx.connected_markets == ["cn"]
    assert yfinance.connected_markets == []
    assert tdx.downloads == [("000001.SZ", "cn", 2, 3)]
    assert frame.iloc[0]["close"] == 1.0


def test_data_source_registry_honors_preferred_source_id() -> None:
    tdx = _Source("data.tdx")
    yfinance = _Source("data.yfinance")
    registry = DataSourceRegistry(
        (
            _contribution("data.tdx", tdx, ("cn", "us")),
            _contribution("data.yfinance", yfinance, ("cn", "us")),
        ),
        _context(),
        preferred_source_id="data.yfinance",
    )

    registry.connect("us")
    assert registry.source_for("us") is yfinance
    assert tdx.connected_markets == []
    assert yfinance.connected_markets == ["us"]


def test_data_source_registry_rejects_duplicate_source_ids() -> None:
    source = _Source("data.duplicate")

    with pytest.raises(SlotConfigurationError, match="duplicate data source"):
        DataSourceRegistry(
            (
                _contribution("data.duplicate", source, ("cn",)),
                _contribution("data.duplicate", source, ("us",)),
            ),
            _context(),
        )


def test_data_source_registry_rejects_unsupported_market() -> None:
    registry = DataSourceRegistry(
        (_contribution("data.tdx", _Source("data.tdx"), ("cn",)),),
        _context(),
    )

    with pytest.raises(SlotConfigurationError, match="no data source supports market: us"):
        registry.source_for("us")


def test_data_source_registry_supports_sources_with_no_arg_connect() -> None:
    source = _NoArgConnectSource("data.yfinance")
    registry = DataSourceRegistry(
        (_contribution("data.yfinance", source, ("us",)),),
        _context(),
    )

    registry.connect("us")

    assert registry.is_connected() is True
    assert source.connected_markets == ["<none>"]


def test_data_source_registry_supports_sources_with_keyword_market_connect() -> None:
    source = _KeywordConnectSource("data.keyword")
    registry = DataSourceRegistry(
        (_contribution("data.keyword", source, ("us",)),),
        _context(),
    )

    registry.connect("us")

    assert registry.is_connected() is True
    assert source.connected_markets == ["us"]


def test_data_source_registry_reconnects_when_market_changes() -> None:
    source = _Source("data.tdx")
    registry = DataSourceRegistry(
        (_contribution("data.tdx", source, ("cn", "us")),),
        _context(),
    )

    registry.connect("cn")
    registry.download_kline("AAPL", "us")

    assert source.connected_markets == ["cn", "us"]
    assert source.downloads == [("AAPL", "us", 0, 800)]


def _contribution(
    source_id: str,
    source: _Source,
    markets: tuple[str, ...],
) -> DataSourceContribution:
    return DataSourceContribution(
        source_id=source_id,
        factory=lambda _context, value=source: value,
        markets=markets,
        capabilities=("market_data.ohlcv",),
    )


def _context() -> SlotContext:
    return SlotContext(settings=object(), feature_flags={"slot_platform": True})

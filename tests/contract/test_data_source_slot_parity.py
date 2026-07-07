"""Data source slot consumer parity tests (Sprint 040)."""

from __future__ import annotations

import pandas as pd
import pytest

from doge.application.contracts.request import ScanMarketRequest
from doge.bootstrap.gateway_factories import market as market_factories
from doge.bootstrap.gateway_factories import use_cases as use_case_factories
from doge.bootstrap.runtime_factories import slots as slots_module
from doge.config import reset_settings
from doge.infrastructure.data_source.tdx import TDXDataSource
from doge.platform.slots import (
    DataSourceContribution,
    ISlot,
    SlotConfigurationError,
    SlotContribution,
    SlotContext,
    SlotHealth,
    SlotManifest,
    SlotProvides,
    SlotRegistry,
    SlotType,
)
from doge.products.market.data_sources import DataSourceRegistry

_ALL_FEATURE_VARS = [
    "DOGE_FEATURE_RUN_SUMMARY_API",
    "DOGE_FEATURE_PLATFORM_OBJECTS",
    "DOGE_FEATURE_WORKFLOW_TEMPLATES",
    "DOGE_FEATURE_CAPABILITY_REGISTRY",
    "DOGE_FEATURE_RUNTIME_OUTBOX_PUBLISHER",
    "DOGE_FEATURE_PYTHON_ANALYSIS_ENABLED",
    "DOGE_FEATURE_SLOT_PLATFORM",
    "DOGE_FEATURE_SLOT_GOVERNANCE",
    "DOGE_FEATURE_SLOT_WATCHER",
    "DOGE_FEATURE_SLOT_UI",
    "DOGE_FEATURE_SLOT_ENFORCEMENT",
    "DOGE_FEATURE_SLOT_LOADER",
    "DOGE_FEATURE_SLOT_INSTALL",
]


class _StockRepo:
    def __init__(self) -> None:
        self.ensure_schema_markets: list[str] = []
        self.saved: list[tuple[str, pd.DataFrame]] = []

    def ensure_schema(self, market: str) -> None:
        self.ensure_schema_markets.append(market)

    def list_distinct_tickers(self, market: str) -> list[str]:
        return []

    def save_prices(self, market: str, df: pd.DataFrame) -> None:
        self.saved.append((market, df.copy()))


class _Source:
    def __init__(self, source_id: str = "data.custom") -> None:
        self.source_id = source_id
        self.connected = False
        self.connected_markets: list[str] = []
        self.downloads: list[tuple[str, str]] = []

    def connect(self, market: str = "cn") -> None:
        self.connected = True
        self.connected_markets.append(market)

    def disconnect(self) -> None:
        self.connected = False

    def is_connected(self) -> bool:
        return self.connected

    def download_kline(self, ticker: str, market: str, start: int = 0, count: int = 800):
        self.downloads.append((ticker, market))
        return pd.DataFrame(
            [
                {
                    "date": "2026-07-07",
                    "open": 10.0,
                    "high": 11.0,
                    "low": 9.0,
                    "close": 10.5,
                    "volume": 1000,
                    "amount": 10500.0,
                }
            ]
        )

    def get_latest_market_date(self, market: str) -> str:
        return "2026-07-07"


class _DataSlot(ISlot):
    def __init__(
        self,
        slot_id: str,
        *,
        source_id: str,
        source: _Source,
        markets: tuple[str, ...] = ("cn", "us"),
    ) -> None:
        self._slot_id = slot_id
        self._source_id = source_id
        self._source = source
        self._markets = markets

    def manifest(self) -> SlotManifest:
        return SlotManifest(
            schema_version=1,
            id=self._slot_id,
            name="Test Data Source Slot",
            version="1.0.0",
            type=SlotType.DATA,
            owner="slot-tests",
            maturity="experimental",
            description="Test data source slot.",
            entrypoint="tests.contract.test_data_source_slot_parity.DataSlot",
            provides=SlotProvides(capabilities=("market_data.ohlcv",)),
            health=SlotHealth(status="experimental"),
            feature_flags=("slot_platform",),
        )

    def resolve(self, context: SlotContext) -> SlotContribution:
        return SlotContribution(
            slot_id=self._slot_id,
            data_sources=(
                DataSourceContribution(
                    source_id=self._source_id,
                    factory=lambda _context: self._source,
                    markets=self._markets,
                    capabilities=("market_data.ohlcv",),
                ),
            ),
        )


def test_data_slot_off_returns_no_registry(monkeypatch) -> None:
    _strip_feature_env(monkeypatch)
    reset_settings()

    assert slots_module.build_slot_aware_data_source() is None


def test_default_data_source_factory_preserves_tdx_when_slot_platform_off(monkeypatch) -> None:
    _strip_feature_env(monkeypatch)
    reset_settings()

    data_source = market_factories.build_tdx_data_source()

    assert isinstance(data_source, TDXDataSource)


def test_preferred_tdx_server_preserves_direct_tdx_even_when_slot_platform_on(monkeypatch) -> None:
    _strip_feature_env(monkeypatch, keep={"DOGE_FEATURE_SLOT_PLATFORM"})
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    reset_settings()

    data_source = market_factories.build_tdx_data_source(preferred_server="127.0.0.1")

    assert isinstance(data_source, TDXDataSource)
    assert data_source.preferred_server == "127.0.0.1"


def test_slot_platform_returns_data_source_registry_with_tdx_first(monkeypatch) -> None:
    _strip_feature_env(monkeypatch, keep={"DOGE_FEATURE_SLOT_PLATFORM"})
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    reset_settings()

    data_source = market_factories.build_tdx_data_source()

    assert isinstance(data_source, DataSourceRegistry)
    assert data_source.source_ids[:2] == ("data.tdx", "data.yfinance")


def test_scan_market_use_case_uses_slot_data_source_registry(monkeypatch) -> None:
    source = _Source("data.custom")
    registry = SlotRegistry()
    registry.register(_DataSlot("data.custom_slot", source_id="data.custom", source=source))
    monkeypatch.setattr(slots_module, "build_builtin_slot_registry", lambda: registry)
    _strip_feature_env(monkeypatch, keep={"DOGE_FEATURE_SLOT_PLATFORM"})
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    reset_settings()
    stock_repo = _StockRepo()
    use_case = use_case_factories.build_scan_market_use_case(
        stock_repo=stock_repo,
        file_scanner=object(),
        refresh_views_callable=None,
    )

    response = use_case.execute(
        ScanMarketRequest(market="cn", tickers=["000001.SZ"])
    )

    assert response.success_count == 1
    assert source.connected_markets == ["cn"]
    assert source.downloads == [("000001.SZ", "cn")]
    assert stock_repo.ensure_schema_markets == ["cn"]
    assert stock_repo.saved[0][0] == "cn"
    assert stock_repo.saved[0][1].iloc[0]["ticker"] == "000001.SZ"


def test_duplicate_data_source_contribution_fails_fast(monkeypatch) -> None:
    registry = SlotRegistry()
    registry.register(
        _DataSlot("data.one", source_id="data.duplicate", source=_Source("one"))
    )
    registry.register(
        _DataSlot("data.two", source_id="data.duplicate", source=_Source("two"))
    )
    monkeypatch.setattr(slots_module, "build_builtin_slot_registry", lambda: registry)
    _strip_feature_env(monkeypatch, keep={"DOGE_FEATURE_SLOT_PLATFORM"})
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    reset_settings()

    with pytest.raises(SlotConfigurationError, match="duplicate data source"):
        slots_module.build_slot_aware_data_source()


def _strip_feature_env(monkeypatch, keep: set[str] | None = None) -> None:
    keep = keep or set()
    for var in _ALL_FEATURE_VARS:
        if var not in keep:
            monkeypatch.delenv(var, raising=False)

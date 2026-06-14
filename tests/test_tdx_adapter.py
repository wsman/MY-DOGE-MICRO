"""Unit tests for the TDX MarketDataSource adapter (S004-004 / ADR-0004).

These tests MOCK both the ``opentdx`` package and the relevant
:mod:`micro.tdx_downloader` helpers — no network, no live TDX server
(test-independence rules in ``.claude/rules/test-standards.md`` and the
forbidden "network-dependent tests without isolation" pattern in ADR-0001).

Coverage targets (mirroring ``tests/test_yfinance_adapter.py`` and the
S004-004 spec):

1. Port conformance: ``isinstance(TDXDataSource(), IMarketDataSource)``.
2. Connection lifecycle (connect -> is_connected True; disconnect -> False).
3. ``download_kline`` normalizes to the canonical 8-column frame.
4. CN ticker -> ``(MARKET.SH/SZ/BJ, code)`` remap drives ``stock_kline``.
5. US goods_kline path.
6. ``count`` truncation (via ``_bars_to_df`` ``max_rows=120``).
7. Empty bars -> ``None``.
8. Transient exception -> bounded retry -> ``None`` (no raise).
9. ``get_latest_market_date`` success + failure -> ``None``.
10. opentdx-absent regression: constructable, is_connected()==False,
    download_kline -> None, no ModuleNotFoundError.
"""
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pandas as pd
import pytest

# Make src/ importable without depending on package install state.

from doge.core.ports.data_source import IMarketDataSource  # noqa: E402
from doge.infrastructure.data_source.tdx import (  # noqa: E402
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_DELAY,
    TDXDataSource,
)


# ---------------------------------------------------------------------------
# Fake opentdx module + fake TdxClient
# ---------------------------------------------------------------------------
class FakeTdxClient:
    """Minimal fake of the opentdx ``TdxClient`` surface used by the adapter."""

    def __init__(self, stock_kline_bars=None, goods_kline_bars=None,
                 stock_kline_errors=None, goods_kline_errors=None,
                 stock_calls=None, goods_calls=None):
        self._stock_bars = stock_kline_bars
        self._goods_bars = goods_kline_bars
        self._stock_errors = list(stock_kline_errors or [])
        self._goods_errors = list(goods_kline_errors or [])
        self.stock_calls = stock_calls if stock_calls is not None else []
        self.goods_calls = goods_calls if goods_calls is not None else []
        # quotation_client / ex_quotation_client must support .disconnect()
        self.quotation_client = MagicMock()
        self.ex_quotation_client = MagicMock()

    def stock_kline(self, market, code, period, start=0, count=800):
        self.stock_calls.append((market, code, period, start, count))
        if self._stock_errors:
            raise self._stock_errors.pop(0)
        return list(self._stock_bars) if self._stock_bars is not None else []

    def goods_kline(self, ex_market, ticker, period, start=0, count=800):
        self.goods_calls.append((ex_market, ticker, period, start, count))
        if self._goods_errors:
            raise self._goods_errors.pop(0)
        return list(self._goods_bars) if self._goods_bars is not None else []


def _make_bars(rows, dt_key="datetime"):
    """Build a list of TDX-shaped bar dicts (one per row).

    CN ``stock_kline`` returns bars keyed by ``'datetime'``; US ``goods_kline``
    uses ``'date_time'``. ``_bars_to_df`` handles both — we control the key
    here so we can exercise each path deterministically.
    """
    bars = []
    for r in rows:
        bars.append({
            dt_key: pd.Timestamp(r["date"]),
            "open": r["open"], "high": r["high"],
            "low": r["low"], "close": r["close"],
            "vol": r["volume"], "amount": r.get("amount", 0.0),
        })
    return bars


@pytest.fixture
def _fake_opentdx(monkeypatch):
    """Install a fake opentdx package with the const enums the adapter needs.

    The fake ``MARKET`` exposes ``.SH / .SZ / .BJ`` as distinct sentinels so
    tests can assert that the CN ticker remap selected the right one.
    """
    market = SimpleNamespace(SH=object(), SZ=object(), BJ=object())
    ex_market = SimpleNamespace(US_STOCK=object())
    period = SimpleNamespace(DAILY=object())

    fake_const = SimpleNamespace(MARKET=market, EX_MARKET=ex_market, PERIOD=period)
    monkeypatch.setitem(sys.modules, "opentdx", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "opentdx.const", fake_const)
    monkeypatch.setitem(sys.modules, "opentdx.tdxClient", SimpleNamespace())
    return {"MARKET": market, "EX_MARKET": ex_market, "PERIOD": period}


@pytest.fixture
def _patch_micro_helpers(monkeypatch):
    """Patch the ``micro.tdx_downloader`` helpers the adapter imports lazily.

    Returns a dict of mocks so individual tests can configure behaviour.
    """
    fake_mod = MagicMock()
    fake_find = MagicMock(return_value=(None, None))
    fake_bars_to_df = MagicMock(return_value=None)
    fake_ticker_remap = MagicMock(return_value=(None, "000000"))
    fake_latest = MagicMock(return_value=None)
    fake_mod.find_working_server = fake_find
    fake_mod._bars_to_df = fake_bars_to_df
    fake_mod._ticker_to_market_code = fake_ticker_remap
    fake_mod._get_latest_market_date = fake_latest
    # CN_SERVERS / US_SERVERS are accessed at module top in the real module —
    # they are not used by the adapter (it reads from settings), but we still
    # expose them in case other test paths import the fake module.
    fake_mod.CN_SERVERS = ["1.1.1.1"]
    fake_mod.US_SERVERS = ["2.2.2.2"]
    monkeypatch.setitem(sys.modules, "micro.tdx_downloader", fake_mod)
    return {
        "module": fake_mod,
        "find_working_server": fake_find,
        "_bars_to_df": fake_bars_to_df,
        "_ticker_to_market_code": fake_ticker_remap,
        "_get_latest_market_date": fake_latest,
    }


# ---------------------------------------------------------------------------
# 1. Port conformance
# ---------------------------------------------------------------------------
def test_tdx_datasource_implements_port():
    assert isinstance(TDXDataSource(), IMarketDataSource)


# ---------------------------------------------------------------------------
# 2. Connection lifecycle (TDX holds a real connection)
# ---------------------------------------------------------------------------
def test_connect_lifecycle_reports_connected_state(_fake_opentdx, _patch_micro_helpers, monkeypatch):
    # Arrange — find_working_server returns a fake client + host.
    fake_client = FakeTdxClient()
    _patch_micro_helpers["find_working_server"].return_value = (fake_client, "1.1.1.1")

    # Act / Assert — disconnected by default
    ds = TDXDataSource()
    assert ds.is_connected() is False
    ds.connect("cn")
    assert ds.is_connected() is True
    ds.disconnect()
    assert ds.is_connected() is False
    # disconnect() must have torn down the quotation client.
    fake_client.quotation_client.disconnect.assert_called_once()


def test_connect_with_no_server_leaves_disconnected(_fake_opentdx, _patch_micro_helpers):
    # Arrange — find_working_server returns (None, None) (server probe failed).
    _patch_micro_helpers["find_working_server"].return_value = (None, None)

    ds = TDXDataSource()
    ds.connect("cn")
    assert ds.is_connected() is False


# ---------------------------------------------------------------------------
# 3. download_kline normalizes to the canonical 8-column frame
# ---------------------------------------------------------------------------
def test_download_kline_normalizes_canonical_columns(_fake_opentdx, _patch_micro_helpers, monkeypatch):
    # Arrange — a live client + a real _bars_to_df that returns the canonical
    # 8-column frame (mirrors the real helper's output contract).
    canonical = pd.DataFrame({
        "date": ["2026-06-09", "2026-06-10"],
        "open": [10.0, 10.5], "high": [11.0, 12.0], "low": [9.5, 10.2],
        "close": [10.5, 11.8], "volume": [1000, 2000], "amount": [1.0, 2.0],
        "ticker": ["600000.SH", "600000.SH"],
    })
    fake_client = FakeTdxClient(stock_kline_bars=_make_bars([
        {"date": "2026-06-09", "open": 10.0, "high": 11.0, "low": 9.5, "close": 10.5, "volume": 1000},
        {"date": "2026-06-10", "open": 10.5, "high": 12.0, "low": 10.2, "close": 11.8, "volume": 2000},
    ]))
    _patch_micro_helpers["_bars_to_df"].return_value = canonical

    ds = TDXDataSource()
    ds._client = fake_client  # bypass connect() — direct injection

    # Act
    df = ds.download_kline("600000.SH", "cn")

    # Assert — canonical 8 columns in order
    assert df is not None
    assert list(df.columns) == ["date", "open", "high", "low", "close", "volume", "amount", "ticker"]
    assert (df["ticker"] == "600000.SH").all()


def test_download_kline_returns_none_when_no_client(_fake_opentdx, _patch_micro_helpers):
    # No connect() — _client stays None.
    ds = TDXDataSource()
    assert ds.download_kline("AAPL", "us") is None


# ---------------------------------------------------------------------------
# 4. CN ticker -> (MARKET.SH/SZ/BJ, code) remap drives stock_kline
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("ticker_suffix, expected_market_attr", [
    (".SH", "SH"),
    (".SZ", "SZ"),
    (".BJ", "BJ"),
])
def test_download_kline_cn_ticker_remap_drives_stock_kline(
    ticker_suffix, expected_market_attr,
    _fake_opentdx, _patch_micro_helpers,
):
    # Arrange — _ticker_to_market_code returns the enum for the suffix under
    # test. The real helper maps .SH -> MARKET.SH etc.
    market_enum = getattr(_fake_opentdx["MARKET"], expected_market_attr)
    _patch_micro_helpers["_ticker_to_market_code"].return_value = (market_enum, "600000")
    _patch_micro_helpers["_bars_to_df"].return_value = pd.DataFrame({
        "date": ["2026-06-09"],
        "open": [10.0], "high": [11.0], "low": [9.5], "close": [10.5],
        "volume": [1000], "amount": [1.0], "ticker": [f"600000{ticker_suffix}"],
    })
    fake_client = FakeTdxClient(stock_kline_bars=[{"datetime": pd.Timestamp("2026-06-09")}])

    ds = TDXDataSource()
    ds._client = fake_client

    # Act
    ds.download_kline(f"600000{ticker_suffix}", "cn", count=120)

    # Assert — stock_kline was called with the mapped market enum + bare code
    assert len(fake_client.stock_calls) == 1
    called_market, called_code, _period, _start, _count = fake_client.stock_calls[0]
    assert called_market is market_enum
    assert called_code == "600000"


# ---------------------------------------------------------------------------
# 5. US goods_kline path
# ---------------------------------------------------------------------------
def test_download_kline_us_uses_goods_kline(_fake_opentdx, _patch_micro_helpers):
    # Arrange — _bars_to_df returns a valid canonical frame.
    _patch_micro_helpers["_bars_to_df"].return_value = pd.DataFrame({
        "date": ["2026-06-09"],
        "open": [100.0], "high": [110.0], "low": [99.0], "close": [105.0],
        "volume": [1000], "amount": [0.0], "ticker": ["AAPL"],
    })
    fake_client = FakeTdxClient(goods_kline_bars=[{"date_time": pd.Timestamp("2026-06-09")}])

    ds = TDXDataSource()
    ds._client = fake_client

    # Act
    df = ds.download_kline("AAPL", "us", count=120)

    # Assert — goods_kline was called (not stock_kline); EX_MARKET.US_STOCK used
    assert df is not None
    assert len(fake_client.goods_calls) == 1
    called_ex, called_ticker, _period, _start, _count = fake_client.goods_calls[0]
    assert called_ex is _fake_opentdx["EX_MARKET"].US_STOCK
    assert called_ticker == "AAPL"
    assert len(fake_client.stock_calls) == 0


# ---------------------------------------------------------------------------
# 6. count truncation (via _bars_to_df max_rows=120)
# ---------------------------------------------------------------------------
def test_download_kline_passes_count_through_to_kline_call(_fake_opentdx, _patch_micro_helpers):
    # Arrange — _bars_to_df returns a frame so we can assert the call args.
    _patch_micro_helpers["_bars_to_df"].return_value = pd.DataFrame({
        "date": ["2026-06-09"],
        "open": [1.0], "high": [1.0], "low": [1.0], "close": [1.0],
        "volume": [1], "amount": [0.0], "ticker": ["600000.SH"],
    })
    market_enum = _fake_opentdx["MARKET"].SH
    _patch_micro_helpers["_ticker_to_market_code"].return_value = (market_enum, "600000")
    fake_client = FakeTdxClient(stock_kline_bars=[{"datetime": pd.Timestamp("2026-06-09")}])

    ds = TDXDataSource()
    ds._client = fake_client

    # Act — request count=50
    ds.download_kline("600000.SH", "cn", start=10, count=50)

    # Assert — count + start forwarded to stock_kline; _bars_to_df received
    # max_rows=120 (the canonical TDX window cap).
    _mkt, _code, _period, called_start, called_count = fake_client.stock_calls[0]
    assert called_start == 10
    assert called_count == 50
    # _bars_to_df is called as _bars_to_df(bars, ticker, max_rows=120) — the
    # max_rows is passed by keyword, so it lives in kwargs.
    call = _patch_micro_helpers["_bars_to_df"].call_args
    _bars_arg, ticker_arg = call.args
    assert ticker_arg == "600000.SH"
    assert call.kwargs.get("max_rows") == 120


# ---------------------------------------------------------------------------
# 7. Empty bars -> None
# ---------------------------------------------------------------------------
def test_download_kline_returns_none_for_empty_bars(_fake_opentdx, _patch_micro_helpers):
    # Arrange — stock_kline returns [] (empty list).
    market_enum = _fake_opentdx["MARKET"].SH
    _patch_micro_helpers["_ticker_to_market_code"].return_value = (market_enum, "600000")
    fake_client = FakeTdxClient(stock_kline_bars=[])

    ds = TDXDataSource()
    ds._client = fake_client

    # Act
    df = ds.download_kline("600000.SH", "cn")

    # Assert — empty bars short-circuit before _bars_to_df is called
    assert df is None
    _patch_micro_helpers["_bars_to_df"].assert_not_called()


# ---------------------------------------------------------------------------
# 8. Transient exception -> bounded retry -> None (no raise)
# ---------------------------------------------------------------------------
def test_download_kline_retries_on_error_then_returns_none(_fake_opentdx, _patch_micro_helpers):
    # Arrange — every stock_kline call raises; _bars_to_df never reached.
    market_enum = _fake_opentdx["MARKET"].SH
    _patch_micro_helpers["_ticker_to_market_code"].return_value = (market_enum, "600000")
    fake_client = FakeTdxClient(
        stock_kline_bars=[],
        stock_kline_errors=[RuntimeError("server reset")] * 3,
    )

    ds = TDXDataSource(max_retries=3, retry_delay=0)
    ds._client = fake_client

    # Act — MUST NOT raise
    df = ds.download_kline("600000.SH", "cn")

    # Assert — 3 attempts made, returns None, _bars_to_df never called
    assert df is None
    assert len(fake_client.stock_calls) == 3
    _patch_micro_helpers["_bars_to_df"].assert_not_called()


def test_download_kline_retries_then_succeeds(_fake_opentdx, _patch_micro_helpers):
    # Arrange — first call errors, second returns bars.
    market_enum = _fake_opentdx["MARKET"].SH
    _patch_micro_helpers["_ticker_to_market_code"].return_value = (market_enum, "600000")
    _patch_micro_helpers["_bars_to_df"].return_value = pd.DataFrame({
        "date": ["2026-06-09"],
        "open": [1.0], "high": [1.0], "low": [1.0], "close": [1.0],
        "volume": [1], "amount": [0.0], "ticker": ["600000.SH"],
    })
    fake_client = FakeTdxClient(
        stock_kline_bars=[{"datetime": pd.Timestamp("2026-06-09")}],
        stock_kline_errors=[RuntimeError("transient")],
    )

    ds = TDXDataSource(max_retries=3, retry_delay=0)
    ds._client = fake_client

    # Act
    df = ds.download_kline("600000.SH", "cn")

    # Assert — retried once then succeeded
    assert df is not None
    assert len(fake_client.stock_calls) == 2


# ---------------------------------------------------------------------------
# 9. get_latest_market_date
# ---------------------------------------------------------------------------
def test_get_latest_market_date_success(_fake_opentdx, _patch_micro_helpers):
    # Arrange
    _patch_micro_helpers["_get_latest_market_date"].return_value = "2026-06-10"
    fake_client = FakeTdxClient()

    ds = TDXDataSource()
    ds._client = fake_client

    # Act
    latest = ds.get_latest_market_date("cn")

    # Assert
    assert latest == "2026-06-10"
    _patch_micro_helpers["_get_latest_market_date"].assert_called_once_with(fake_client, "cn")


def test_get_latest_market_date_returns_none_on_failure(_fake_opentdx, _patch_micro_helpers):
    # Arrange — helper raises (offline / empty proxy index); adapter must
    # swallow and return None.
    _patch_micro_helpers["_get_latest_market_date"].side_effect = RuntimeError("offline")
    fake_client = FakeTdxClient()

    ds = TDXDataSource()
    ds._client = fake_client

    # Act — MUST NOT raise
    assert ds.get_latest_market_date("us") is None


def test_get_latest_market_date_returns_none_when_disconnected(_fake_opentdx, _patch_micro_helpers):
    # No connect() — _client is None.
    ds = TDXDataSource()
    assert ds.get_latest_market_date("cn") is None
    _patch_micro_helpers["_get_latest_market_date"].assert_not_called()


# ---------------------------------------------------------------------------
# 10. opentdx-absent regression (mirror test_scanner_opentdx_optional.py)
# ---------------------------------------------------------------------------
@pytest.fixture
def _no_opentdx(monkeypatch):
    """Simulate a clean process where opentdx is not installed.

    Mirrors the ``_blocking_import`` fixture in
    ``tests/unit/micro/test_scanner_opentdx_optional.py``: snapshot and remove
    opentdx + micro modules, install a blocking import hook, then restore on
    teardown.
    """
    to_remove = [
        m for m in sys.modules
        if m == "opentdx" or m.startswith("opentdx.") or m.startswith("micro.")
    ]
    saved = {m: sys.modules.pop(m) for m in to_remove}

    original_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__

    def _blocking_import(name, *args, **kwargs):
        if name == "opentdx" or name.startswith("opentdx."):
            raise ModuleNotFoundError(f"No module named '{name}'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", _blocking_import)

    yield

    for name, mod in saved.items():
        sys.modules[name] = mod
    for name in list(sys.modules):
        if name == "opentdx" or name.startswith("opentdx.") or name.startswith("micro."):
            if name not in saved:
                sys.modules.pop(name, None)


class TestTdxAdapterWithoutOpentdx:
    def test_constructable_without_opentdx(self, _no_opentdx):
        # Module must import cleanly even with opentdx blocked.
        # Re-import the adapter module so its (lazy) imports re-run.
        sys.modules.pop("doge.infrastructure.data_source.tdx", None)
        from doge.infrastructure.data_source.tdx import TDXDataSource as FreshDS
        ds = FreshDS()
        assert ds.is_connected() is False

    def test_connect_returns_silently_without_opentdx(self, _no_opentdx):
        # connect() must NOT raise ModuleNotFoundError — degrade to disconnected.
        sys.modules.pop("doge.infrastructure.data_source.tdx", None)
        from doge.infrastructure.data_source.tdx import TDXDataSource as FreshDS
        ds = FreshDS()
        ds.connect("cn")
        assert ds.is_connected() is False

    def test_download_kline_returns_none_without_opentdx(self, _no_opentdx):
        # No live client means download_kline -> None without raising.
        sys.modules.pop("doge.infrastructure.data_source.tdx", None)
        from doge.infrastructure.data_source.tdx import TDXDataSource as FreshDS
        ds = FreshDS()
        assert ds.download_kline("600000.SH", "cn") is None
        assert ds.get_latest_market_date("cn") is None


# ---------------------------------------------------------------------------
# Defaults (parity with yfinance adapter / ADR-0004 item 3)
# ---------------------------------------------------------------------------
def test_default_retry_policy_matches_adr_0004():
    assert DEFAULT_MAX_RETRIES == 3
    assert DEFAULT_RETRY_DELAY == 5.0

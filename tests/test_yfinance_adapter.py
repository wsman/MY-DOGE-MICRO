"""Unit tests for the yfinance MarketDataSource adapter.

These tests MOCK the ``yfinance`` package (no network) to satisfy test
independence rules in ``.claude/rules/test-standards.md`` and the forbidden
"network-dependent tests without isolation" pattern in ADR-0001.

Coverage targets (per BUG B acceptance):
- data normalization (columns, dtypes)
- empty-result handling
- retry-on-error path (rate-limit + generic error)
- CN ticker remap (.SH -> .SS)
- connection lifecycle no-ops
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Make src/ importable without depending on package install state.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from doge.infrastructure.data_source.yfinance import (  # noqa: E402
    DEFAULT_PERIOD_DAYS,
    YFinanceDataSource,
    _is_rate_limited,
)
from doge.core.ports.data_source import IMarketDataSource  # noqa: E402


# ---------------------------------------------------------------------------
# Fake yfinance module
# ---------------------------------------------------------------------------
class FakeYFinance:
    """Minimal fake of the yfinance module surface used by the adapter."""

    def __init__(self, frames_by_ticker, errors_by_ticker=None, call_log=None):
        self.frames_by_ticker = frames_by_ticker
        self.errors_by_ticker = errors_by_ticker or {}
        self.call_log = call_log if call_log is not None else []

    def download(self, ticker, period="120d", interval="1d", progress=False):
        self.call_log.append((ticker, period))
        # Replay any configured errors before returning data, so retry logic
        # can be exercised. errors_by_ticker maps ticker -> list[exc]; each
        # call pops one exc until the list is empty.
        if ticker in self.errors_by_ticker and self.errors_by_ticker[ticker]:
            raise self.errors_by_ticker[ticker].pop(0)
        frame = self.frames_by_ticker.get(ticker)
        if frame is None:
            return pd.DataFrame()
        return frame.copy()


def _make_raw_frame(rows, multi_index=True, ticker="AAPL"):
    """Build a yfinance-shaped frame (TitleCase cols, DatetimeIndex)."""
    idx = pd.DatetimeIndex(pd.to_datetime([r["date"] for r in rows]))
    data = {
        "Open": [r["open"] for r in rows],
        "High": [r["high"] for r in rows],
        "Low": [r["low"] for r in rows],
        "Close": [r["close"] for r in rows],
        "Volume": [r["volume"] for r in rows],
    }
    df = pd.DataFrame(data, index=idx)
    if multi_index:
        df.columns = pd.MultiIndex.from_product([df.columns, [ticker]])
    return df


# ---------------------------------------------------------------------------
# Port conformance
# ---------------------------------------------------------------------------
def test_yfinance_datasource_implements_port():
    assert isinstance(YFinanceDataSource(), IMarketDataSource)


# ---------------------------------------------------------------------------
# Connection lifecycle (yfinance is stateless — these are no-ops)
# ---------------------------------------------------------------------------
def test_connect_lifecycle_reports_connected_state():
    ds = YFinanceDataSource()
    assert ds.is_connected() is False
    ds.connect()
    assert ds.is_connected() is True
    ds.disconnect()
    assert ds.is_connected() is False


# ---------------------------------------------------------------------------
# Normalization: columns, dtypes, ticker column
# ---------------------------------------------------------------------------
def test_download_kline_normalizes_columns_and_dtypes(monkeypatch):
    # Arrange — one row of OHLCV from yfinance
    rows = [
        {"date": "2026-06-09", "open": 10.0, "high": 11.0, "low": 9.5, "close": 10.5, "volume": 1000},
        {"date": "2026-06-10", "open": 10.5, "high": 12.0, "low": 10.2, "close": 11.8, "volume": 2000},
    ]
    fake = FakeYFinance({"AAPL": _make_raw_frame(rows, ticker="AAPL")})
    monkeypatch.setitem(sys.modules, "yfinance", fake)

    # Act
    ds = YFinanceDataSource()
    ds.connect()
    df = ds.download_kline("AAPL", "us")

    # Assert — canonical 8 columns in order
    assert list(df.columns) == ["date", "open", "high", "low", "close", "volume", "amount", "ticker"]
    # date is a string, OHLCV numeric
    assert df["date"].dtype == object
    assert str(df["open"].dtype).startswith("float")
    assert str(df["close"].dtype).startswith("float")
    # pandas may use int64 or uint64 depending on platform; just check integer-kind
    assert np.issubdtype(df["volume"].dtype, np.integer)
    # ticker column populated
    assert (df["ticker"] == "AAPL").all()
    # amount is the documented placeholder
    assert (df["amount"] == 0.0).all()
    # sorted ascending by date
    assert df["date"].tolist() == ["2026-06-09", "2026-06-10"]


def test_download_kline_cn_ticker_remaps_sh_to_ss(monkeypatch):
    # Arrange
    rows = [{"date": "2026-06-09", "open": 5.0, "high": 5.2, "low": 4.9, "close": 5.1, "volume": 500}]
    call_log = []
    fake = FakeYFinance({"600000.SS": _make_raw_frame(rows, ticker="600000.SS")}, call_log=call_log)
    monkeypatch.setitem(sys.modules, "yfinance", fake)

    # Act
    ds = YFinanceDataSource()
    df = ds.download_kline("600000.SH", "cn")

    # Assert — yfinance received the .SS suffix; output keeps canonical .SH
    assert call_log == [("600000.SS", "120d")]
    assert (df["ticker"] == "600000.SH").all()


def test_download_kline_trims_to_count(monkeypatch):
    # Arrange — 5 rows requested, but count caps to last 2
    rows = [
        {"date": f"2026-06-0{i}", "open": float(i), "high": float(i + 1), "low": float(i), "close": float(i), "volume": i * 100}
        for i in range(1, 6)
    ]
    fake = FakeYFinance({"AAPL": _make_raw_frame(rows, ticker="AAPL")})
    monkeypatch.setitem(sys.modules, "yfinance", fake)

    # Act
    ds = YFinanceDataSource()
    df = ds.download_kline("AAPL", "us", count=2)

    # Assert
    assert len(df) == 2
    assert df["date"].iloc[-1] == "2026-06-05"


# ---------------------------------------------------------------------------
# Empty / missing data
# ---------------------------------------------------------------------------
def test_download_kline_returns_none_for_empty_ticker(monkeypatch):
    # Arrange — yfinance returns an empty frame
    fake = FakeYFinance({})
    monkeypatch.setitem(sys.modules, "yfinance", fake)

    # Act
    ds = YFinanceDataSource(max_retries=1, retry_delay=0)
    df = ds.download_kline("BOGUS", "us")

    # Assert
    assert df is None


def test_download_kline_returns_none_when_columns_missing(monkeypatch):
    # Arrange — frame with no recognizable OHLCV columns
    weird = pd.DataFrame({"foo": [1, 2]}, index=pd.DatetimeIndex(pd.to_datetime(["2026-06-09", "2026-06-10"])))
    weird.columns = pd.MultiIndex.from_product([weird.columns, ["AAPL"]])
    fake = FakeYFinance({"AAPL": weird})
    monkeypatch.setitem(sys.modules, "yfinance", fake)

    # Act
    ds = YFinanceDataSource()
    df = ds.download_kline("AAPL", "us")

    # Assert
    assert df is None


# ---------------------------------------------------------------------------
# Retry-on-error path
# ---------------------------------------------------------------------------
def test_is_rate_limited_detects_429_signals():
    assert _is_rate_limited(Exception("HTTP 429 Too Many Requests")) is True
    assert _is_rate_limited(Exception("Rate limit exceeded")) is True
    assert _is_rate_limited(Exception("connection reset")) is False


def test_download_kline_retries_on_rate_limit_then_succeeds(monkeypatch):
    # Arrange — first call raises a 429, second returns data
    rows = [{"date": "2026-06-09", "open": 10.0, "high": 11.0, "low": 9.5, "close": 10.5, "volume": 1000}]
    call_log = []
    fake = FakeYFinance(
        {"AAPL": _make_raw_frame(rows, ticker="AAPL")},
        errors_by_ticker={"AAPL": [Exception("HTTP 429 Too Many Requests")]},
        call_log=call_log,
    )
    monkeypatch.setitem(sys.modules, "yfinance", fake)

    # Act — retry_delay=0 to keep the test fast
    ds = YFinanceDataSource(max_retries=3, retry_delay=0)
    df = ds.download_kline("AAPL", "us")

    # Assert — retried once then succeeded
    assert df is not None
    assert len(call_log) == 2
    assert (df["ticker"] == "AAPL").all()


def test_download_kline_returns_none_after_exhausting_retries(monkeypatch):
    # Arrange — every call raises a generic (non-rate-limit) error
    call_log = []
    fake = FakeYFinance(
        {},
        errors_by_ticker={"AAPL": [RuntimeError("boom"), RuntimeError("boom"), RuntimeError("boom")]},
        call_log=call_log,
    )
    monkeypatch.setitem(sys.modules, "yfinance", fake)

    # Act
    ds = YFinanceDataSource(max_retries=3, retry_delay=0)
    df = ds.download_kline("AAPL", "us")

    # Assert — all retries consumed, returns None (no raise)
    assert df is None
    assert len(call_log) == 3


# ---------------------------------------------------------------------------
# get_latest_market_date
# ---------------------------------------------------------------------------
def test_get_latest_market_date_returns_last_index(monkeypatch):
    # Arrange
    rows = [
        {"date": "2026-06-09", "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1},
        {"date": "2026-06-10", "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1},
    ]
    fake = FakeYFinance({"SPY": _make_raw_frame(rows, ticker="SPY")})
    monkeypatch.setitem(sys.modules, "yfinance", fake)

    # Act
    ds = YFinanceDataSource(max_retries=1, retry_delay=0)
    latest = ds.get_latest_market_date("us")

    # Assert
    assert latest == "2026-06-10"


def test_get_latest_market_date_returns_none_on_failure(monkeypatch):
    fake = FakeYFinance({})
    monkeypatch.setitem(sys.modules, "yfinance", fake)

    ds = YFinanceDataSource(max_retries=1, retry_delay=0)
    assert ds.get_latest_market_date("us") is None


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
def test_default_period_days_matches_tdx_window():
    # Document the 120d alignment between TDX and yfinance defaults.
    assert DEFAULT_PERIOD_DAYS == 120

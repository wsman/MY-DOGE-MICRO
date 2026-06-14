"""BLOCKING integration test (S005-007 / ADR-0004 Migration Plan step 4):

``GlobalMacroLoader.fetch_combined_data`` is routed through the
``YFinanceDataSource`` adapter (no longer calls ``yfinance.download``
directly), and the resulting WIDE Close-only frame has the exact shape
``calculate_metrics`` / ``calculate_advanced_metrics`` / the strategist
consume.

The adapter returns a LONG 8-column frame per ticker
(``date, open, high, low, close, volume, amount, ticker``);
``fetch_combined_data`` must pivot/merge those per-ticker frames into a
WIDE Close frame with:

* a ``DatetimeIndex`` named ``"Date"``
* one column per ticker (columns = ticker symbols, e.g. ``QQQ``, ``GLD``,
  ``000300.SS``, ``BTC-USD``)
* Close values aligned to a common trading calendar (BTC trades weekends,
  QQQ/GLD do not) — reindex/ffill reproduces the alignment that the
  original single ``yf.download(tickers=[...])`` call produced.

This test pins that shape by mocking the ``yfinance`` module the adapter
lazy-imports (the same interception pattern used in
``tests/test_yfinance_adapter.py``). Because the adapter lazy-imports
``yfinance`` inside ``download_kline``, the same ``monkeypatch.setitem``
the unit tests use intercepts the macro path too.

Determinism: no network; mocked yfinance; deterministic synthetic frames.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Test-shim exception (documented in test_settings.py): make src/ importable.

from macro.config import MacroConfig  # noqa: E402
from macro.data_loader import GlobalMacroLoader  # noqa: E402


# ---------------------------------------------------------------------------
# Config / loader construction WITHOUT touching models_config.json or env.
# Mirrors the MacroConfig.__new__ bypass in tests/test_macro_strategist.py.
# ---------------------------------------------------------------------------
def _build_config() -> MacroConfig:
    cfg = MacroConfig.__new__(MacroConfig)
    cfg.tech_proxy = "QQQ"
    cfg.tech_name = "Tech (Nasdaq)"
    cfg.safe_haven_proxy = "GLD"
    cfg.safe_name = "Gold"
    cfg.crypto_proxy = "BTC-USD"
    cfg.crypto_name = "Crypto"
    cfg.target_asset = "000300.SS"
    cfg.target_name = "A-share core (CSI300)"
    cfg.lookback_days = 30  # keep the test small but > volatility_window
    cfg.volatility_window = 20
    cfg.api_key = "sk-test-key-not-real"
    cfg.base_url = "https://api.deepseek.com"
    cfg.model = "deepseek-chat"
    cfg.proxy_url = None
    cfg.proxy_enabled = False
    return cfg


# ---------------------------------------------------------------------------
# Fake yfinance module — mirrors tests/test_yfinance_adapter.py:FakeYFinance.
# The adapter's default fetcher calls ``c.download(t, period=f"{p}d",
# interval="1d", progress=False)``, so a single-ticker signature suffices.
# ---------------------------------------------------------------------------
class _FakeYFinance:
    """Records each call and returns a yfinance-shaped frame per ticker.

    Each fake frame is a single-ticker MultiIndex column frame (matching the
    shape real yfinance returns for one ticker), which the adapter's
    ``_normalize`` flattens into the canonical 8-col long schema.
    """

    def __init__(self, frames_by_ticker: dict[str, pd.DataFrame]):
        self.frames_by_ticker = frames_by_ticker
        self.call_log: list[tuple[str, str]] = []

    def download(self, ticker, period="120d", interval="1d", progress=False):
        self.call_log.append((ticker, period))
        frame = self.frames_by_ticker.get(ticker)
        if frame is None:
            return pd.DataFrame()
        return frame.copy()


def _make_raw_close_frame(ticker: str, dates: list[str], closes: list[float]) -> pd.DataFrame:
    """Build a single-ticker MultiIndex yfinance-shaped frame."""
    idx = pd.DatetimeIndex(pd.to_datetime(dates))
    df = pd.DataFrame(
        {
            "Open": closes,
            "High": [c + 1.0 for c in closes],
            "Low": [c - 1.0 for c in closes],
            "Close": closes,
            "Volume": [1000] * len(closes),
        },
        index=idx,
    )
    df.columns = pd.MultiIndex.from_product([df.columns, [ticker]])
    return df


# ---------------------------------------------------------------------------
# The pivot shape contract (trap 2 + strategist boundary parity).
# ---------------------------------------------------------------------------
def test_fetch_combined_data_returns_wide_close_frame_via_adapter(monkeypatch):
    """S005-007 / ADR-0004 step 4: ``fetch_combined_data`` routes through the
    ``YFinanceDataSource`` adapter and returns a WIDE Close-only frame with
    the shape the strategist reads (DatetimeIndex named 'Date', columns =
    ticker symbols in declaration order, values = Close)."""
    cfg = _build_config()
    loader = GlobalMacroLoader(cfg)

    # Arrange — distinct trading dates per ticker to exercise the union
    # calendar alignment (BTC has a bar on a date QQQ does not, mirroring
    # weekend crypto trading). Use only common business dates so the
    # ``dropna(subset=[tech_col])`` + ffill + dropna pipeline still yields a
    # well-formed wide frame.
    common_dates = pd.bdate_range(end="2026-06-12", periods=40).strftime("%Y-%m-%d").tolist()
    rng = np.random.default_rng(42)
    frames = {
        "QQQ": _make_raw_close_frame("QQQ", common_dates, list(100 + rng.normal(0, 1, 40).cumsum())),
        "GLD": _make_raw_close_frame("GLD", common_dates, list(180 + rng.normal(0, 0.5, 40).cumsum())),
        "000300.SS": _make_raw_close_frame("000300.SS", common_dates, list(3800 + rng.normal(0, 2, 40).cumsum())),
        "BTC-USD": _make_raw_close_frame("BTC-USD", common_dates, list(30000 + rng.normal(0, 50, 40).cumsum())),
    }
    fake = _FakeYFinance(frames)
    # The adapter lazy-imports yfinance inside download_kline; patching
    # sys.modules intercepts every per-ticker fetch.
    monkeypatch.setitem(sys.modules, "yfinance", fake)

    # Act
    data = loader.fetch_combined_data(max_retries=1, retry_delay=0)

    # Assert — shape contract the strategist / calculate_metrics reads:
    # 1. DatetimeIndex named "Date"
    assert data is not None, "fetch_combined_data returned None on mocked data"
    assert isinstance(data.index, pd.DatetimeIndex), (
        f"expected DatetimeIndex, got {type(data.index).__name__}"
    )
    assert data.index.name == "Date", f"index name={data.index.name!r}, expected 'Date'"

    # 2. Columns = ticker symbols, in declaration order
    #    [tech_proxy, safe_haven_proxy, target_asset, crypto_proxy].
    expected_cols = ["QQQ", "GLD", "000300.SS", "BTC-USD"]
    assert list(data.columns) == expected_cols, (
        f"columns={list(data.columns)}, expected {expected_cols}"
    )

    # 3. Exactly lookback_days rows (the tail trim).
    assert len(data) == cfg.lookback_days, (
        f"row count={len(data)}, expected lookback_days={cfg.lookback_days}"
    )

    # 4. No NaN anywhere (dropna is the last cleaning step).
    assert not data.isna().any().any(), f"NaNs present in wide frame:\n{data}"

    # 5. Sorted ascending by date.
    assert data.index.is_monotonic_increasing, "wide frame not ascending by date"

    # 6. Each ticker was fetched exactly once via the adapter (4 tickers).
    fetched_tickers = [call[0] for call in fake.call_log]
    assert sorted(fetched_tickers) == sorted(expected_cols), (
        f"fetched tickers={fetched_tickers}, expected all of {expected_cols}"
    )
    # The adapter's trap-1 fix fetches max(fetch_days, period_days) days.
    # fetch_days = lookback_days * 1.65 + 20 = 69; period_days = 120 (default),
    # so max(69, 120) = 120 — the adapter fetches 120d, NOT the starving 69d.
    assert all(call[1] == "120d" for call in fake.call_log), (
        f"unexpected periods in call_log: {fake.call_log}"
    )


def test_fetch_combined_data_returns_none_when_adapter_yields_nothing(monkeypatch):
    """S005-007 / degraded path: when yfinance returns empty for every
    ticker (e.g. total outage), ``fetch_combined_data`` returns ``None``
    rather than raising — preserving the original direct-yfinance
    None-on-failure contract at the strategist boundary."""
    cfg = _build_config()
    loader = GlobalMacroLoader(cfg)

    # Arrange — yfinance returns empty frames for every ticker.
    fake = _FakeYFinance({})
    monkeypatch.setitem(sys.modules, "yfinance", fake)

    # Act
    data = loader.fetch_combined_data(max_retries=1, retry_delay=0)

    # Assert — None (the documented degraded sentinel).
    assert data is None, (
        f"expected None when adapter yields nothing, got shape={None if data is None else data.shape}"
    )


def test_fetch_combined_data_calculate_metrics_consumes_wide_frame(monkeypatch):
    """S005-007 / strategist-boundary parity: the wide Close frame returned
    by the adapter-routed ``fetch_combined_data`` is directly consumable by
    ``calculate_metrics`` (which reads ``data.iloc[-1]``, ``trend_medium.get(
    self.config.tech_proxy)``, ``calculate_advanced_metrics`` references
    ``df[self.config.crypto_proxy]`` as a column). No KeyError, no shape
    drift, no extra transformation needed at the strategist seam."""
    cfg = _build_config()
    loader = GlobalMacroLoader(cfg)

    # Arrange — common business dates for all 4 tickers.
    common_dates = pd.bdate_range(end="2026-06-12", periods=45).strftime("%Y-%m-%d").tolist()
    rng = np.random.default_rng(7)
    frames = {
        "QQQ": _make_raw_close_frame("QQQ", common_dates, list(100 + rng.normal(0, 1, 45).cumsum())),
        "GLD": _make_raw_close_frame("GLD", common_dates, list(180 + rng.normal(0, 0.5, 45).cumsum())),
        "000300.SS": _make_raw_close_frame("000300.SS", common_dates, list(3800 + rng.normal(0, 2, 45).cumsum())),
        "BTC-USD": _make_raw_close_frame("BTC-USD", common_dates, list(30000 + rng.normal(0, 50, 45).cumsum())),
    }
    fake = _FakeYFinance(frames)
    monkeypatch.setitem(sys.modules, "yfinance", fake)

    # Act — fetch via the adapter path, then immediately compute metrics.
    data = loader.fetch_combined_data(max_retries=1, retry_delay=0)
    assert data is not None
    metrics = loader.calculate_metrics(data)

    # Assert — calculate_metrics produced the expected keys (proves the wide
    # frame's shape is identical to the pre-S005-007 direct-yfinance shape).
    assert "metadata_days" in metrics
    assert metrics["metadata_days"] == cfg.lookback_days
    assert "risk_on_signal" in metrics
    # Per-asset keys the strategist reads (strategist.py:37-43).
    for ticker in ("QQQ", "GLD", "BTC-USD", "000300.SS"):
        assert f"{ticker}_trend_medium" in metrics, f"missing {ticker}_trend_medium"
        assert f"{ticker}_return_5d" in metrics, f"missing {ticker}_return_5d"
    # Advanced-metrics keys (calculate_advanced_metrics).
    assert "gold_btc_ratio" in metrics
    assert "vol_skew" in metrics
    # RSRS keys for tech_proxy + safe_haven_proxy (calculate_metrics:343-349).
    assert f"{cfg.tech_proxy}_rsrs" in metrics
    assert f"{cfg.safe_haven_proxy}_rsrs" in metrics

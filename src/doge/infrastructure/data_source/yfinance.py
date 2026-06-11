"""yfinance data source adapter — implements the MarketDataSource port.

This adapter wraps the third-party :mod:`yfinance` package and normalizes its
output to the canonical OHLCV frame defined by
``doge.core.ports.data_source.IMarketDataSource.download_kline``:

    columns: ``date, open, high, low, close, volume, amount, ticker``

Retry/backoff behavior mirrors the rate-limit handling already proven in
``src/macro/data_loader.py`` (``GlobalMacroLoader.fetch_combined_data``):
a bounded retry loop with a fixed delay that recognises Yahoo Finance
HTTP 429 / "Too Many Requests" responses. Keeping the retry logic inside the
adapter (rather than the caller) means every interface layer that depends on
the :class:`IMarketDataSource` port gets the same offline/degraded tolerance
for free, satisfying ADR-0001 ("network calls must tolerate retries, caching,
and degraded/offline behavior") and ADR-0004.

Design notes
------------
* The adapter holds **no persistent connection** (yfinance is stateless HTTP),
  so :meth:`connect` / :meth:`disconnect` / :meth:`is_connected` are no-ops
  that exist only to satisfy the port contract shared with TDX.
* ``yfinance`` is imported lazily inside :meth:`download_kline` so that unit
  tests can inject a mock without the real package being installed, and so
  that simply importing this module never performs a network round-trip.
* ``amount`` (turnover) is not provided by yfinance OHLCV; the column is
  populated with ``0.0`` so downstream readers (which expect the canonical
  8-column frame) do not need a special case. See CDD section 3.
"""

from __future__ import annotations

import logging
import time
from typing import Callable, Optional

import pandas as pd

from doge.core.ports.data_source import IMarketDataSource

logger = logging.getLogger(__name__)

# Canonical output column order — MUST match IMarketDataSource.download_kline
_OUTPUT_COLUMNS = ["date", "open", "high", "low", "close", "volume", "amount", "ticker"]

# yfinance OHLCV columns -> canonical columns. yfinance uses TitleCase names.
_COLUMN_MAP = {
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Adj Close": "close",  # when auto_adjust=False the adjusted close wins
    "Volume": "volume",
}

# Default request budget — see CDD section 9 (Integration Requirements).
# 120d matches TDXReader.MAX_DAYS and the downloader --max-bars default so a
# yfinance refresh yields the same window width as a TDX refresh.
DEFAULT_PERIOD_DAYS = 120
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 5.0  # seconds; matches macro/data_loader.py default


def _is_rate_limited(error: BaseException) -> bool:
    """Return True when *error* looks like a Yahoo Finance rate-limit response.

    Reuses the same heuristic string match as
    ``src/macro/data_loader.py`` (lines 94-97): "Rate", "429", or
    "Too Many Requests" in the error message.
    """
    message = str(error)
    return any(token in message for token in ("Rate", "429", "Too Many Requests"))


class YFinanceDataSource(IMarketDataSource):
    """yfinance-backed implementation of the :class:`IMarketDataSource` port.

    Parameters
    ----------
    max_retries:
        Number of retry attempts on a rate-limited or transient error before
        giving up and returning ``None`` (degraded/offline behavior).
    retry_delay:
        Fixed delay in seconds between retries. Mirrors the
        ``retry_delay`` parameter of ``GlobalMacroLoader.fetch_combined_data``.
    period_days:
        Lookback window in trading days. Defaults to ``120`` so a yfinance
        refresh produces the same row count as a TDX refresh.
    """

    def __init__(
        self,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        period_days: int = DEFAULT_PERIOD_DAYS,
    ) -> None:
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.period_days = period_days
        self._connected = False

    # ------------------------------------------------------------------
    # Connection lifecycle (yfinance is stateless HTTP; these are no-ops)
    # ------------------------------------------------------------------
    def connect(self) -> None:
        """Mark the adapter as connected.

        yfinance has no persistent session to open; this exists only to
        satisfy the shared :class:`IMarketDataSource` contract.
        """
        self._connected = True

    def disconnect(self) -> None:
        """Mark the adapter as disconnected."""
        self._connected = False

    def is_connected(self) -> bool:
        """Return True iff :meth:`connect` was called more recently than :meth:`disconnect`."""
        return self._connected

    # ------------------------------------------------------------------
    # yfinance -> canonical ticker mapping
    # ------------------------------------------------------------------
    @staticmethod
    def _to_yf_ticker(ticker: str, market: str) -> str:
        """Map a canonical ticker to the yfinance exchange suffix.

        yfinance uses ``.SS`` for Shanghai and ``.SZ`` for Shenzhen, while the
        rest of this project uses TDX-style ``.SH`` / ``.SZ``. This mirrors the
        remap in ``src/micro/industry_analyzer.py`` (line 184).
        US tickers pass through unchanged.
        """
        if market == "cn" and ticker.endswith(".SH"):
            return ticker.replace(".SH", ".SS")
        return ticker

    # ------------------------------------------------------------------
    # Core operation
    # ------------------------------------------------------------------
    def download_kline(
        self,
        ticker: str,
        market: str,
        start: int = 0,
        count: int = 800,
    ) -> Optional[pd.DataFrame]:
        """Download daily OHLCV for *ticker* via yfinance and normalize it.

        Args:
            ticker: Canonical ticker (e.g. ``"600000.SH"`` or ``"AAPL"``).
            market: ``"cn"`` or ``"us"``.
            start: Ignored — yfinance is date/period based, not offset based.
                Accepted for port-compatibility with TDX.
            count: Upper bound on rows to return. The yfinance request asks
                for ``period_days`` and the result is trimmed to the most
                recent ``count`` rows.

        Returns:
            Canonical 8-column DataFrame, or ``None`` if every retry fails
            (network down, rate-limited, empty ticker). Never raises for
            transient/empty conditions — callers treat ``None`` as the
            degraded signal.

        Note:
            ``start`` is intentionally unused; it is documented here rather
            than silenced so reviewers understand the semantic mismatch
            between the offset-based TDX contract and the period-based
            yfinance API.
        """
        del start  # offset semantics do not apply to yfinance (see docstring)

        yf_ticker = self._to_yf_ticker(ticker, market)

        # Lazy import so tests can monkeypatch and so module import is free.
        import yfinance as yf  # type: ignore[import-not-found]

        raw_df = self._fetch_with_retry(yf, yf_ticker)
        if raw_df is None or raw_df.empty:
            logger.warning("yfinance returned empty data for %s (%s)", ticker, yf_ticker)
            return None

        normalized = self._normalize(raw_df, ticker)

        if normalized is None or normalized.empty:
            return None

        if count and len(normalized) > count:
            normalized = normalized.tail(count).reset_index(drop=True)
        return normalized

    def get_latest_market_date(self, market: str) -> Optional[str]:
        """Return the most recent trading date observable via yfinance.

        Uses a liquid proxy index per market (``000300.SS`` for CN, ``SPY``
        for US) and reads the last index value. Returns ``None`` if the
        lookup fails (offline / rate-limited).
        """
        import yfinance as yf  # type: ignore[import-not-found]

        proxy = "000300.SS" if market == "cn" else "SPY"
        yf_proxy = self._to_yf_ticker(proxy, market)
        raw_df = self._fetch_with_retry(
            yf, yf_proxy, period_days=5, fetcher=lambda c, t, p: c.download(t, period=f"{p}d", interval="1d", progress=False)
        )
        if raw_df is None or raw_df.empty:
            return None
        try:
            last_index = raw_df.index[-1]
            return pd.Timestamp(last_index).strftime("%Y-%m-%d")
        except Exception:  # pragma: no cover - defensive
            return None

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _fetch_with_retry(
        self,
        yf_module,
        yf_ticker: str,
        period_days: Optional[int] = None,
        fetcher: Optional[Callable] = None,
    ) -> Optional[pd.DataFrame]:
        """Call yfinance with bounded retry on transient/rate-limit errors.

        ``fetcher`` lets callers override the exact yfinance call (used by
        :meth:`get_latest_market_date`); the default downloads a single
        ticker's daily history. The retry loop is the shared "retry on 429"
        policy also used by ``macro/data_loader.py``.
        """
        days = self.period_days if period_days is None else period_days
        if fetcher is None:
            def fetcher(c, t, p):  # noqa: ANN001 - yfinance signature
                return c.download(t, period=f"{p}d", interval="1d", progress=False)

        last_error: Optional[BaseException] = None
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    logger.info("yfinance retry %d/%d for %s", attempt + 1, self.max_retries, yf_ticker)
                    time.sleep(self.retry_delay)
                data = fetcher(yf_module, yf_ticker, days)
                if data is None or data.empty:
                    # Empty often means rate-limit; keep retrying.
                    last_error = RuntimeError("empty response (possible rate limit)")
                    continue
                return data
            except Exception as err:  # noqa: BLE001 - yfinance raises varied errors
                last_error = err
                if _is_rate_limited(err):
                    logger.warning("yfinance rate-limited on %s; retrying in %ss", yf_ticker, self.retry_delay)
                else:
                    logger.error("yfinance fetch error for %s: %s", yf_ticker, err)
        logger.error("yfinance exhausted %d retries for %s: %s", self.max_retries, yf_ticker, last_error)
        return None

    @staticmethod
    def _normalize(raw_df: pd.DataFrame, ticker: str) -> Optional[pd.DataFrame]:
        """Normalize a yfinance frame to the canonical 8-column schema.

        * Flattens the MultiIndex columns yfinance returns for a single
          ticker (e.g. ``("Close", "AAPL")``).
        * Maps TitleCase OHLCV columns to lowercase canonical names.
        * Builds a string ``date`` column from the yfinance DatetimeIndex.
        * Adds ``amount`` (turnover) as ``0.0`` — yfinance daily OHLCV does
          not include turnover.
        * Adds the canonical ``ticker`` column.
        * Coerces OHLCV to numeric dtypes and drops NaN-OHLC rows.
        """
        df = raw_df.copy()

        # Flatten MultiIndex columns produced by single-ticker downloads.
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Rename to canonical lowercase names, keeping only known columns.
        renamed = {}
        for col in df.columns:
            mapped = _COLUMN_MAP.get(str(col))
            if mapped:
                renamed[col] = mapped
        df = df.rename(columns=renamed)

        needed = {"open", "high", "low", "close", "volume"}
        if not needed.issubset(df.columns):
            logger.warning("yfinance frame for %s missing OHLCV columns: %s", ticker, list(df.columns))
            return None

        # Date column from the DatetimeIndex.
        df["date"] = pd.to_datetime(df.index).strftime("%Y-%m-%d")

        # amount (turnover) is not available from yfinance daily OHLCV.
        df["amount"] = 0.0
        df["ticker"] = ticker

        # Coerce numeric dtypes and drop rows missing core OHLC.
        for col in ("open", "high", "low", "close", "volume", "amount"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=["open", "high", "low", "close"])

        df = df.sort_values("date").reset_index(drop=True)
        return df[_OUTPUT_COLUMNS]

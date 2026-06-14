"""TDX (通达信) server data source adapter.

Implements :class:`doge.core.ports.data_source.IMarketDataSource` by wrapping
the helpers in :mod:`micro.tdx_downloader` (:func:`find_working_server`,
:func:`_ticker_to_market_code`, :func:`_bars_to_df`, and
:func:`_get_latest_market_date`). This is the ADR-0004 migration step that
promotes the TDX adapter from a stub to a real port implementation.

Design notes
------------
* Unlike :class:`YFinanceDataSource` (stateless HTTP), the TDX adapter holds a
  **real connection lifecycle**: :meth:`connect` probes TDX quotation servers
  via :func:`find_working_server` and stores the resulting ``TdxClient``;
  :meth:`is_connected` reflects that state; :meth:`disconnect` tears down the
  underlying ``quotation_client`` (and the US extended-hours
  ``ex_quotation_client`` when present).
* ``opentdx`` is an optional ``[tdx]`` extra. To honour ADR-0001's
  offline/degraded contract (and ADR-0004 item 4 — "Lazy third-party import"),
  the opentdx import is performed lazily **inside method bodies**, never at
  module top. When opentdx is absent, every method degrades cleanly:
  ``connect`` leaves ``is_connected() == False``, ``download_kline`` returns
  ``None``, ``get_latest_market_date`` returns ``None``. **Never raises**
  ``ModuleNotFoundError``.
* Servers, ports and timeout come from :func:`doge.config.get_settings` ``.tdx``
  (:class:`TDXConfig`) — never hardcoded (ADR-0001 forbidden pattern
  ``hardcoded_runtime_params_in_implementation``).
* ``download_kline`` reuses :func:`micro.tdx_downloader._bars_to_df`, which
  already produces the canonical 8-column frame
  ``["date", "open", "high", "low", "close", "volume", "amount", "ticker"]``.
* A bounded local retry loop wraps the per-ticker fetch and **returns None on
  exhaustion** (ADR-0004 item 2 — "No raises for transient failure"). The
  shared ``_retry.py`` helper extraction is deferred (ADR-0004 Migration Plan
  step 2); the loop stays local for now, mirroring the yfinance adapter.
* The adapter performs **no persistence**: no ``save_stock_data_custom``, no
  SQLite/DuckDB writes (ADR-0001 forbidden pattern
  ``direct_sqlite_import_in_interface``; ADR-0004 item 6 — "Decoupled
  persistence"). Persistence is the caller's responsibility.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import pandas as pd

from doge.config import get_settings
from doge.core.ports.data_source import IMarketDataSource
from doge.infrastructure.data_source._retry import fetch_with_retry

logger = logging.getLogger(__name__)

# Canonical output column order — MUST match IMarketDataSource.download_kline.
_OUTPUT_COLUMNS = ["date", "open", "high", "low", "close", "volume", "amount", "ticker"]

# Retry policy defaults — mirror the yfinance adapter and ADR-0004 item 3.
# Sourced from ADR-0004 / macro/data_loader.py (3 retries, 5s delay).
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 5.0


class TDXDataSource(IMarketDataSource):
    """TDX (TongDaXin) quotation-server implementation of the
    :class:`IMarketDataSource` port.

    Parameters
    ----------
    max_retries:
        Number of retry attempts on a transient error before giving up and
        returning ``None`` (degraded/offline behavior). Mirrors the
        ``YFinanceDataSource`` parameter and ADR-0004 item 3 defaults.
    retry_delay:
        Fixed delay in seconds between retries. Mirrors the
        ``YFinanceDataSource`` parameter and ``macro/data_loader.py`` default.
    """

    def __init__(
        self,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
    ) -> None:
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        # ``_client`` is the live ``TdxClient`` (or ``None`` when disconnected /
        # never connected / opentdx absent). ``_market`` remembers which server
        # family was probed so :meth:`disconnect` knows whether the US extended
        # quotation client needs tearing down too.
        self._client: Any = None
        self._market: Optional[str] = None

    # ------------------------------------------------------------------
    # Connection lifecycle (TDX holds a real TCP session to a quote server)
    # ------------------------------------------------------------------
    def connect(self, market: str = "cn") -> None:
        """Probe TDX servers and store the first working ``TdxClient``.

        When ``opentdx`` is not installed, or no server can be reached, this
        method leaves :meth:`is_connected` returning ``False`` and never
        raises (ADR-0004 offline-tolerance contract).

        Args:
            market: ``"cn"`` (port 7709, CN_SERVERS) or ``"us"`` (port 7727,
                US_SERVERS). Defaults to ``"cn"`` to match the dominant TDX
                workflow.
        """
        cfg = get_settings().tdx
        servers = list(cfg.cn_servers if market == "cn" else cfg.us_servers)

        # Lazy import: opentdx is an optional [tdx] extra. find_working_server
        # itself guards the TdxClient import (micro/tdx_downloader.py:33-38),
        # but importing it pulls in the rest of micro.tdx_downloader which we
        # want to defer so this module imports cleanly without opentdx.
        try:
            from micro.tdx_downloader import find_working_server
        except ImportError:  # pragma: no cover - defensive (micro is required)
            logger.warning("micro.tdx_downloader unavailable; TDXDataSource cannot connect")
            self._client = None
            self._market = None
            return

        try:
            client, _host = find_working_server(servers, market, timeout=cfg.timeout)
        except Exception as err:  # noqa: BLE001 - server probe raises varied errors
            logger.warning("TDX connect probe failed for market=%s: %s", market, err)
            client = None

        self._client = client
        self._market = market if client is not None else None

    def disconnect(self) -> None:
        """Tear down the underlying TDX quotation client(s).

        Safe to call when already disconnected or when opentdx is absent
        (no-op in both cases).
        """
        client = self._client
        if client is None:
            return
        try:
            client.quotation_client.disconnect()
        except Exception as err:  # noqa: BLE001 - teardown errors are non-fatal
            logger.warning("TDX quotation_client disconnect failed: %s", err)
        if self._market == "us":
            ex_client = getattr(client, "ex_quotation_client", None)
            if ex_client is not None:
                try:
                    ex_client.disconnect()
                except Exception as err:  # noqa: BLE001 - teardown non-fatal
                    logger.warning("TDX ex_quotation_client disconnect failed: %s", err)
        self._client = None
        self._market = None

    def is_connected(self) -> bool:
        """Return ``True`` iff :meth:`connect` succeeded and stored a client."""
        return self._client is not None

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
        """Download daily OHLCV for *ticker* from a TDX server.

        Args:
            ticker: Canonical ticker (e.g. ``"600000.SH"`` for CN or ``"AAPL"``
                for US). CN tickers are remapped via
                :func:`micro.tdx_downloader._ticker_to_market_code`.
            market: ``"cn"`` or ``"us"``.
            start: Bar offset from earliest history (passed straight to
                ``stock_kline`` / ``goods_kline``).
            count: Max bars to fetch. ``_bars_to_df`` further caps the returned
                frame to ``max_rows=120`` (the canonical TDX window), so callers
                requesting more than 120 rows still receive the bounded frame.

        Returns:
            Canonical 8-column DataFrame, or ``None`` when opentdx is absent,
            no connection is open, the server returns empty bars, or every
            retry attempt fails. **Never raises** for transient/empty/opentdx-
            absent conditions (ADR-0004 items 2 + 4).
        """
        client = self._client
        if client is None:
            logger.warning("TDX download_kline called with no live client (ticker=%s)", ticker)
            return None

        # Lazy imports — see module docstring for the rationale.
        try:
            from micro.tdx_downloader import (
                _bars_to_df,
                _ticker_to_market_code,
            )
        except ImportError:  # pragma: no cover - defensive (micro is required)
            logger.warning("micro.tdx_downloader unavailable; cannot fetch TDX kline")
            return None

        # Resolve the opentdx market enum lazily so this method works regardless
        # of whether the top-level micro.tdx_downloader import succeeded with
        # opentdx present. If opentdx is absent we degrade to None — but that
        # case is already handled by ``client is None`` above, since
        # connect() cannot have succeeded without opentdx.
        try:
            from opentdx.const import EX_MARKET, PERIOD  # type: ignore[import-not-found]
        except ImportError:  # pragma: no cover - client is None when opentdx absent
            logger.warning("opentdx unavailable; cannot resolve kline enums")
            return None

        bars = self._fetch_with_retry(
            client,
            ticker,
            market,
            start,
            count,
            _ticker_to_market_code,
            EX_MARKET,
            PERIOD,
        )
        if not bars:
            logger.info("TDX returned empty bars for %s (%s)", ticker, market)
            return None

        df = _bars_to_df(bars, ticker, max_rows=120)
        if df is None or df.empty:
            return None

        # Defensive column-order normalization — _bars_to_df already returns
        # the canonical 8 columns, but we re-index to guarantee the contract
        # (and to protect against future drift in micro.tdx_downloader).
        for col in _OUTPUT_COLUMNS:
            if col not in df.columns:
                logger.warning("TDX frame for %s missing column %s", ticker, col)
                return None
        return df[_OUTPUT_COLUMNS]

    def get_latest_market_date(self, market: str) -> Optional[str]:
        """Return the most recent trading date observable via TDX.

        Wraps :func:`micro.tdx_downloader._get_latest_market_date`. Returns
        ``None`` when opentdx is absent, no connection is open, or the lookup
        fails (offline / empty proxy index). Never raises.
        """
        client = self._client
        if client is None:
            return None

        try:
            from micro.tdx_downloader import _get_latest_market_date
        except ImportError:  # pragma: no cover - defensive
            return None

        try:
            return _get_latest_market_date(client, market)
        except Exception as err:  # noqa: BLE001 - lookup failures degrade to None
            logger.warning("TDX get_latest_market_date failed for %s: %s", market, err)
            return None

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _fetch_with_retry(
        self,
        client: Any,
        ticker: str,
        market: str,
        start: int,
        count: int,
        ticker_remap: Any,
        ex_market_enum: Any,
        period_enum: Any,
    ) -> Optional[list]:
        """Call ``stock_kline`` / ``goods_kline`` with bounded retry.

        Mirrors ``YFinanceDataSource._fetch_with_retry`` but operates against
        the TDX client's per-market kline methods. Returns ``None`` on
        exhaustion (never raises) — ADR-0004 item 2.

        Implementation delegates to the shared ``_retry.fetch_with_retry``
        primitive (S005-006 / ADR-0004 Migration Plan step 2). The TDX path
        historically retried EVERY caught exception (no non-retryable
        filtering), so this passes ``is_retryable=lambda _: True`` to
        preserve that behavior bit-for-bit.

        Args:
            client: Live ``TdxClient`` (opentdx).
            ticker: Canonical ticker to fetch.
            market: ``"cn"`` or ``"us"``.
            start/count: Forwarded to the kline call.
            ticker_remap: ``micro.tdx_downloader._ticker_to_market_code``
                (passed in for testability).
            ex_market_enum: ``opentdx.const.EX_MARKET`` (lazy import, passed in).
            period_enum: ``opentdx.const.PERIOD`` (lazy import, passed in).

        Returns:
            ``list[dict]`` of bars from the TDX client, or ``None`` if every
            retry attempt failed.
        """
        def _fetch() -> list:
            if market == "cn":
                mkt, code = ticker_remap(ticker)
                # ``mkt`` is None only when the ticker has no recognizable
                # suffix; fall back to SH (the most liquid CN market).
                if mkt is None:  # pragma: no cover - defensive
                    from opentdx.const import MARKET  # type: ignore[import-not-found]
                    mkt = MARKET.SH
                return client.stock_kline(mkt, code, period_enum.DAILY, start=start, count=count)
            return client.goods_kline(
                ex_market_enum.US_STOCK, ticker, period_enum.DAILY,
                start=start, count=count,
            )

        def _on_retry(attempt: int, max_retries: int, exc: BaseException) -> None:
            logger.info(
                "TDX retry %d/%d for %s (%s)",
                attempt, max_retries, ticker, market,
            )
            logger.error("TDX fetch error for %s (%s): %s", ticker, market, exc)

        return fetch_with_retry(
            _fetch,
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
            # TDX historically retried every caught exception — preserve that
            # exact behavior. (The shared helper still treats empty/None
            # results as retryable, which TDX's loop also did implicitly via
            # the empty-bars short-circuit in ``download_kline``.)
            is_retryable=lambda _exc: True,
            on_retry=_on_retry,
            label=f"TDX[{ticker}/{market}]",
        )

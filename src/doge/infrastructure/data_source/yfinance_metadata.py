"""yfinance ticker-metadata adapter — implements ``ITickerMetadataSource``.

This adapter wraps the third-party :mod:`yfinance` ``Ticker.info`` surface and
normalizes the output to the dict contract defined by
``doge.core.ports.metadata.ITickerMetadataSource.get_metadata``:

    {"name": str, "sector": str}

It reuses the same retry/backoff policy as :class:`YFinanceDataSource` and the
shared :mod:`doge.infrastructure.data_source._retry` helper so network failures
and rate-limits degrade to ``None`` rather than crashing callers.
"""

from __future__ import annotations

import logging
from typing import Optional

from doge.config import get_settings
from doge.core.ports.metadata import ITickerMetadataSource
from doge.infrastructure.data_source._retry import fetch_with_retry

logger = logging.getLogger(__name__)

# Default request budget — mirrors YFinanceDataSource for consistency.
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 5.0


class YFinanceMetadataSource(ITickerMetadataSource):
    """yfinance ``.info`` metadata source.

    Parameters
    ----------
    max_retries:
        Number of retry attempts on a rate-limited or transient error before
        giving up and returning ``None``.
    retry_delay:
        Fixed delay in seconds between retries.
    """

    def __init__(
        self,
        max_retries: Optional[int] = None,
        retry_delay: Optional[float] = None,
    ) -> None:
        self._explicit_max_retries = max_retries
        self._explicit_retry_delay = retry_delay

    @property
    def max_retries(self) -> int:
        """Effective max retry count — explicit override or ``YFinanceConfig``."""
        if self._explicit_max_retries is not None:
            return self._explicit_max_retries
        return get_settings().yfinance.max_retries

    @property
    def retry_delay(self) -> float:
        """Effective retry delay — explicit override or ``YFinanceConfig``."""
        if self._explicit_retry_delay is not None:
            return self._explicit_retry_delay
        return get_settings().yfinance.retry_delay

    @staticmethod
    def _to_yf_ticker(ticker: str, market: str) -> str:
        """Map a canonical ticker to the yfinance exchange suffix.

        yfinance uses ``.SS`` for Shanghai and ``.SZ`` for Shenzhen, while the
        rest of this project uses TDX-style ``.SH`` / ``.SZ``. US tickers pass
        through unchanged.
        """
        if market == "cn" and ticker.endswith(".SH"):
            return ticker.replace(".SH", ".SS")
        return ticker

    def get_metadata(self, ticker: str, market: str) -> Optional[dict]:
        """Return ``{'name': ..., 'sector': ...}`` for *ticker* via yfinance.

        Args:
            ticker: Canonical ticker (e.g. ``"600000.SH"`` or ``"AAPL"``).
            market: ``"cn"`` or ``"us"``.

        Returns:
            A dict with at minimum ``name`` and ``sector`` keys, or ``None`` if
            every retry fails (network down, rate-limited, empty ticker).
        """
        if market not in {"cn", "us"}:
            logger.warning("metadata lookup unsupported market: %s", market)
            return None

        yf_ticker = self._to_yf_ticker(ticker, market)

        # Lazy import so tests can monkeypatch and module import stays network-free.
        import yfinance as yf  # type: ignore[import-not-found]

        info = self._fetch_info_with_retry(yf, yf_ticker)
        if not info:
            return None

        name = info.get("shortName") or info.get("longName")
        sector = info.get("sector") or info.get("industry")
        if not name:
            return None

        return {
            "name": name,
            "sector": sector or "Unknown",
        }

    def _fetch_info_with_retry(self, yf_module, yf_ticker: str) -> Optional[dict]:
        """Call ``yf.Ticker(...).info`` with bounded retry."""
        def _fetcher() -> Optional[dict]:
            # yfinance.info can return an empty dict on failure/timeout.
            return yf_module.Ticker(yf_ticker).info or None

        return fetch_with_retry(
            _fetcher,
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
            is_retryable=lambda _: True,  # retry on any exception → None on exhaust
            label=f"yfinance.metadata[{yf_ticker}]",
        )

"""yfinance ticker-metadata adapter — placeholder for the ``.info`` migration.

Full implementation will migrate the live ``yf.Ticker(...).info`` call (plus its
retry loop and in-memory cache) from ``src/micro/industry_analyzer.py:190``. The
stub mirrors the existing ``TDXDataSource`` stub pattern (see
``tdx.py:32,35``): the port is declared and wired so callers and the registry
have a concrete implementation to target, while the real network logic lands in
a follow-on story.
"""

from typing import Optional

from doge.core.ports.metadata import ITickerMetadataSource


class YFinanceMetadataSource(ITickerMetadataSource):
    """yfinance ``.info`` metadata source (stub — full implementation pending)."""

    def get_metadata(self, ticker: str, market: str) -> Optional[dict]:
        """Return ``{'name': ..., 'sector': ...}`` for *ticker*.

        Raises:
            NotImplementedError: the real ``.info`` call has not been migrated
                yet. Tracked by the follow-on story that pulls the logic out of
                ``src/micro/industry_analyzer.py:190``.
        """
        raise NotImplementedError(
            "YFinanceMetadataSource.get_metadata: migrate the yfinance .info "
            "call from src/micro/industry_analyzer.py:190"
        )

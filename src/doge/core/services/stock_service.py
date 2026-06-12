"""Stock query service — pure business logic, no external dependencies.

Replaces the scattered SQL in cli.py, the retired MCP monolith query_stock,
and api/routers/data.py get_kline.
"""

from typing import List

from doge.core.ports.repository import IStockRepository


class StockService:
    """High-level stock data queries."""

    def __init__(self, repo: IStockRepository):
        self._repo = repo

    def query(self, ticker: str, market: str, days: int = 20) -> List[dict]:
        """Get OHLCV + indicators for a ticker."""
        return self._repo.get_prices(ticker, market, days)

    def overview(self, ticker: str, market: str) -> dict:
        """Get stock overview: name, sector, latest price, notes."""
        return self._repo.get_overview(ticker, market)

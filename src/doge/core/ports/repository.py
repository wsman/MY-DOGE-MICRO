"""Abstract repository interfaces (Ports in Ports & Adapters).

Implementations live in doge.infrastructure.database.repositories.
"""

from abc import ABC, abstractmethod
from typing import List, Optional


class IStockRepository(ABC):
    """Interface for stock price data access."""

    @abstractmethod
    def get_prices(
        self,
        ticker: str,
        market: str,
        days: int = 20,
    ) -> List[dict]:
        """Get OHLCV prices for a ticker."""
        ...

    @abstractmethod
    def get_overview(self, ticker: str, market: str) -> dict:
        """Get stock overview: name, sector, latest price, notes."""
        ...

    @abstractmethod
    def get_sync_state(self, tickers: List[str]) -> dict[str, dict]:
        """Return {ticker: {"latest_date": str, "row_count": int}}."""
        ...


class IReportRepository(ABC):
    """Interface for research report / note data access."""

    @abstractmethod
    def list_macro_reports(self, limit: int = 100) -> List[dict]:
        ...

    @abstractmethod
    def get_macro_report(self, report_id: int) -> Optional[dict]:
        ...

    @abstractmethod
    def save_macro_report(self, *, content: str, risk_signal: str,
                          volatility: str, tags: str, analyst: str) -> None:
        ...

    @abstractmethod
    def save_research_report(self, *, title: str, content: str,
                             tags: str, analyst: str) -> None:
        ...

    @abstractmethod
    def add_note(self, *, ticker: str, content: str, market: str,
                 note_type: str, title: Optional[str],
                 tags: Optional[str], price_at_note: Optional[float],
                 source: Optional[str]) -> int:
        ...

    @abstractmethod
    def search_notes(self, query: str, limit: int = 50) -> List[dict]:
        ...

    @abstractmethod
    def list_stock_names(self) -> List[dict]:
        ...

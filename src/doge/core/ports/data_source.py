"""Abstract data source interfaces."""

from abc import ABC, abstractmethod
from typing import List, Optional
import pandas as pd


class IMarketDataSource(ABC):
    """Interface for market data download sources (TDX, yfinance, etc.)."""

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the data source."""
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection."""
        ...

    @abstractmethod
    def download_kline(
        self,
        ticker: str,
        market: str,
        start: int = 0,
        count: int = 800,
    ) -> Optional[pd.DataFrame]:
        """Download K-line data for a single ticker.

        Args:
            ticker: Full ticker code (e.g. "600000.SH")
            market: "cn" or "us"
            start: Bar offset from earliest history
            count: Max bars to fetch

        Returns:
            DataFrame with columns: date, open, high, low, close, volume, amount, ticker
        """
        ...

    @abstractmethod
    def get_latest_market_date(self, market: str) -> Optional[str]:
        """Get the latest trading date from the data source."""
        ...

    @abstractmethod
    def is_connected(self) -> bool:
        ...

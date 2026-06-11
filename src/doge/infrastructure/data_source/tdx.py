"""TDX data source adapter — placeholder for incremental download refactoring.

Full implementation will migrate logic from src/micro/tdx_downloader.py.
"""

from typing import Optional

import pandas as pd

from doge.core.ports.data_source import IMarketDataSource


class TDXDataSource(IMarketDataSource):
    """TDX server data source adapter (stub — full implementation in progress)."""

    def connect(self) -> None:
        pass

    def disconnect(self) -> None:
        pass

    def is_connected(self) -> bool:
        return False

    def download_kline(
        self,
        ticker: str,
        market: str,
        start: int = 0,
        count: int = 800,
    ) -> Optional[pd.DataFrame]:
        raise NotImplementedError("TDXDataSource.download_kline: migrate from tdx_downloader.py")

    def get_latest_market_date(self, market: str) -> Optional[str]:
        raise NotImplementedError("TDXDataSource.get_latest_market_date: migrate from tdx_downloader.py")

"""File-system scanner port for local TDX .day archives.

This port intentionally lives separately from
:class:`~doge.core.ports.data_source.IMarketDataSource`: the data-source port
abstracts remote/network download (TDX server, yfinance), while this port
abstracts reading already-downloaded TDX binary .day files from a local
vipdoc directory.
"""
from abc import ABC, abstractmethod
from typing import Callable, Iterable, Optional

import pandas as pd


ProgressCallback = Callable[[int, str], None]


class ITdxFileScanner(ABC):
    """Port for scanning local TDX .day files into canonical OHLCV frames."""

    @abstractmethod
    def scan_local(
        self,
        market: str,
        tdx_path: str,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> Iterable[pd.DataFrame]:
        """Yield one canonical OHLCV DataFrame per ticker discovered locally.

        Args:
            market: ``"cn"`` or ``"us"``.
            tdx_path: Root TDX vipdoc directory (may be the parent directory;
                implementations auto-correct to ``vipdoc`` if needed).
            progress_callback: Optional ``(percent, message)`` callback.

        Yields:
            DataFrames with columns ``date, open, high, low, close, volume,
            amount, ticker``.
        """
        ...

    @abstractmethod
    def list_tickers(self, market: str, tdx_path: str) -> list[str]:
        """Return the tickers that would be scanned without parsing files."""
        ...

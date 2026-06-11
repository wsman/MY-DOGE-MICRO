"""Abstract cache interfaces."""

from abc import ABC, abstractmethod
from typing import Dict, Optional


class ITickerNameCache(ABC):
    """Interface for ticker name <-> code mapping cache."""

    @abstractmethod
    def get(self, ticker: str) -> Optional[str]:
        """Return the Chinese name for a ticker, or None."""
        ...

    @abstractmethod
    def load(self, market: str) -> Dict[str, str]:
        """Load all ticker names for a market."""
        ...

    @abstractmethod
    def clear(self) -> None:
        ...

"""Abstract ticker metadata source port.

Distinct from ``ITickerNameCache`` (which reads local-JSON ticker-name lookups):
this port captures the *remote* yfinance ``.info`` metadata surface that returns
both a name and a sector for a given ticker. See ADR-0009 for the split
rationale (local file vs network; name string vs name+sector dict).
"""

from abc import ABC, abstractmethod
from typing import Optional


class ITickerMetadataSource(ABC):
    """Interface for remote ticker metadata (name + sector) lookup.

    Implementations call a remote provider (today: yfinance ``Ticker.info``)
    and return a dict carrying at least ``name`` and ``sector``. This is a
    network-backed port, intentionally separate from the file-backed
    :class:`~doge.core.ports.cache.ITickerNameCache`.
    """

    @abstractmethod
    def get_metadata(self, ticker: str, market: str) -> Optional[dict]:
        """Return ``{'name': ..., 'sector': ...}`` for *ticker*, or ``None``.

        Args:
            ticker: Canonical ticker code (e.g. ``"600000.SH"`` or ``"AAPL"``).
            market: Market discriminator (``"cn"`` or ``"us"``); implementations
                may remap suffixes (e.g. ``.SH`` -> ``.SS``) before the remote
                call.

        Returns:
            A dict with at minimum ``name`` and ``sector`` keys, or ``None``
            when the remote provider has no data for *ticker*.
        """
        ...

"""Abstract repository interfaces (Ports in Ports & Adapters).

Implementations live in doge.infrastructure.database.repositories.
"""

from abc import ABC, abstractmethod
from typing import List, Optional


class StorageWriteError(RuntimeError):
    """Raised by storage write paths (``save_prices``) when persistence fails.

    Replaces the legacy swallowed ``except Exception: pass`` in
    ``src/micro/database.py::save_stock_data_custom`` (TR-006). Write paths
    MUST surface failures via this typed exception so callers can decide
    whether to tolerate (per-ticker scan loop) or propagate (single-shot
    write) — silent failure is forbidden under ADR-0003.

    Subclasses ``RuntimeError`` per ADR-0003:133. The original underlying
    exception (sqlite3.IntegrityError, OperationalError, OSError, ...) is
    chained via ``raise StorageWriteError(...) from e`` so ``__cause__``
    preserves the root cause for diagnostics.
    """


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

    @abstractmethod
    def ensure_schema(self, market: str) -> None:
        """Idempotently create the ``stock_prices`` table for ``market``.

        Args:
            market: Market identifier (``"cn"`` or ``"us"``); selects the
                target SQLite database file via centralized settings.

        Raises:
            StorageWriteError: When schema initialization fails. Callers MUST
                NOT see a swallowed failure.

        Notes:
            Replaces the legacy interface-layer ``init_db_custom`` call
            (ADR-0001 forbidden pattern) with a port-backed bootstrap so the
            schema write flows through the single logical writer. See S002-005.
        """
        ...

    @abstractmethod
    def save_prices(self, market: str, frame) -> int:
        """Persist an OHLCV frame to the ``stock_prices`` table.

        Args:
            market: Market identifier (``"cn"`` or ``"us"``); selects the
                target SQLite database file.
            frame: A pandas ``DataFrame`` with columns ``date, open, high,
                low, close, volume, amount, ticker``. The ``ticker`` column
                MUST be present so retention pruning can be applied per-ticker.

        Returns:
            The number of rows appended.

        Raises:
            StorageWriteError: When the underlying write fails (PK violation,
                unwritable path, schema mismatch, ...). The original
                exception is chained via ``__cause__``. Callers MUST NOT see
                a swallowed failure.

        Notes:
            The write is **DESTRUCTIVE** — rows older than the configured
            ``DOGE_RETENTION_DAYS`` (default 730, must be ``>= 730``) are
            deleted per ticker on every call. See ADR-0003 and S002-007.
        """
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

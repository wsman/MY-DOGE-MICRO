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

    @abstractmethod
    def get_kline(self, ticker: str, market: str, days: int = 120) -> List[dict]:
        """Get OHLCV k-line data with moving-average indicators.

        This is the API-facing contract for ``GET
        /api/data/{market}/ticker/{ticker}/kline``. The returned records
        preserve the existing field names ``date, open, high, low, close,
        volume`` plus market-specific indicators:

        - ``cn``: ``ma_5, ma_10, ma_20, ma_60, atr_14``
        - ``us``: ``amount``

        Args:
            ticker: Ticker symbol (e.g. ``"000001.SZ"`` or ``"AAPL"``).
            market: Market identifier (``"cn"`` or ``"us"``).
            days: Number of trading days to return (ascending by date).

        Returns:
            A list of records, ascending by ``date``.
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
    def get_latest_macro_report(self) -> Optional[dict]:
        """Return the single most recent macro report, or ``None``."""
        ...

    @abstractmethod
    def save_macro_report(self, *, content: str, risk_signal: str,
                          volatility: str, tags: str, analyst: str) -> None:
        ...

    @abstractmethod
    def list_research_reports(self, limit: int = 100) -> List[dict]:
        """List research reports ordered newest-first."""
        ...

    @abstractmethod
    def get_research_report(self, report_id: int) -> Optional[dict]:
        """Fetch a single research report by id, or ``None``."""
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

class INoteRepository(ABC):
    """Interface for stock note / annotation data access.

    This port decouples the note domain from the underlying SQLite storage.
    All read methods exclude soft-deleted rows (``deleted_at IS NOT NULL``)
    unless ``include_deleted=True`` is passed. The soft-delete behavior
    mirrors the legacy ``src/ai_analysis/stock_notes.py`` contract.
    """

    @abstractmethod
    def add_note(
        self,
        ticker: str,
        note_text: str,
        *,
        market: str = "cn",
        note_type: str = "comment",
        title: Optional[str] = None,
        tags: Optional[str] = None,
        price_at_note: Optional[float] = None,
        source: Optional[str] = None,
        sentiment: Optional[str] = None,
    ) -> int:
        """Persist a new note and return its auto-generated id.

        Args:
            ticker: Ticker symbol (e.g. ``"000001.SZ"`` or ``"AAPL"``).
            note_text: Free-form note content.
            market: Market identifier (``"cn"`` or ``"us"``).
            note_type: Note category (e.g. ``"comment"``, ``"research"``).
            title: Optional note title.
            tags: Optional comma-separated tag string.
            price_at_note: Optional price snapshot at note creation.
            source: Optional source identifier (e.g. ``"manual"``, ``"ai"``).
            sentiment: Optional sentiment label (e.g. ``"bullish"``, ``"bearish"``).

        Returns:
            The integer ``id`` of the inserted row (``lastrowid``).
        """
        ...

    @abstractmethod
    def delete_note(self, note_id: int) -> bool:
        """Soft-delete a note by id.

        Marks ``deleted_at = <now>`` on the matching active row. Returns
        ``True`` when a row was affected, ``False`` when no active note
        with ``note_id`` exists.
        """
        ...

    @abstractmethod
    def get_notes(
        self,
        ticker: Optional[str] = None,
        include_deleted: bool = False,
    ) -> List[dict]:
        """Return notes, optionally filtered by ticker.

        Args:
            ticker: When given, restrict to this ticker. When ``None``,
                return notes for all tickers.
            include_deleted: When ``True``, include soft-deleted rows.

        Returns:
            List of note records ordered newest-first.
        """
        ...

    @abstractmethod
    def search_notes(self, keyword: str, limit: int = 50) -> List[dict]:
        """Full-text search over note content and title (soft-deleted excluded).

        Args:
            keyword: Substring matched with ``LIKE`` against ``content``
                and ``title``.
            limit: Maximum rows to return (default 50).

        Returns:
            Matching note records ordered newest-first, with columns
            ``ticker, created_at, note_type, title, content``.
        """
        ...

    @abstractmethod
    def get_recent_notes(self, days: int = 7, limit: int = 100) -> List[dict]:
        """Return the most recent notes within a date window.

        Args:
            days: Number of days back from today to include.
            limit: Maximum rows to return (default 100).

        Returns:
            Note records ordered newest-first, with columns
            ``ticker, market, created_at, note_type, title, content, tags``.
        """
        ...

    @abstractmethod
    def list_tracked_tickers(self) -> List[dict]:
        """Return tickers with active notes and their metadata.

        Returns:
            List of dicts with keys ``ticker, market, n, last_note``,
            ordered by ``last_note`` descending.
        """
        ...

    @abstractmethod
    def get_ticker_with_context(self, ticker: str, market: str = "cn") -> dict:
        """Return a composite view of a ticker: prices, name, sector, notes.

        The implementation is adapter-specific: the SQLite adapter may
        return name/sector from ``stock_names`` and delegate price data
        to a DuckDB view (or leave ``prices`` empty if DuckDB is not
        available). Callers should handle missing optional keys gracefully.

        Args:
            ticker: Ticker symbol.
            market: Market identifier (``"cn"`` or ``"us"``).

        Returns:
            A dict with keys such as ``ticker``, ``market``, ``name_cn``,
            ``name_en``, ``sector``, ``industry``, ``price_data`` (list of
            OHLCV dicts), ``notes`` (list of note dicts),
            ``note_count_total`` (int). Optional keys may be present
            depending on adapter capabilities.
        """
        ...


class ISchemaBrowser(ABC):
    """Interface for low-level SQLite schema introspection.

    This port lets the API data-browsing endpoints (``list_tables``,
    ``query_table``, ``stats``) remain decoupled from ``sqlite3`` while still
    supporting the generic table-exploration surface that is not a domain
    stock/report query.
    """

    @abstractmethod
    def list_tables(self, market: str) -> List[str]:
        """Return table names in the database identified by ``market``.

        Args:
            market: One of ``"cn"``, ``"us"``, ``"research"``.

        Returns:
            Sorted list of table names. Missing DB files return ``[]``.
        """
        ...

    @abstractmethod
    def query_table(
        self,
        market: str,
        table_name: str,
        page: int = 1,
        page_size: int = 50,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
    ) -> dict:
        """Return a paginated, optionally filtered/sorted view of ``table_name``.

        Args:
            market: One of ``"cn"``, ``"us"``, ``"research"``.
            table_name: Validated table name in the target DB.
            page: 1-based page index.
            page_size: Rows per page (``1..500``).
            search: Optional substring matched against the first five textual
                columns (combined with ``OR``).
            sort_by: Optional column name to sort by.
            sort_order: ``"asc"`` or ``"desc"``.

        Returns:
            ``{"columns": [...], "rows": [...], "total": int,
            "page": int, "page_size": int}``.

        Raises:
            ValueError: When ``market`` is unknown.
        """
        ...

    @abstractmethod
    def database_stats(self) -> dict:
        """Return row counts per table for all configured databases.

        The implementation resolves the canonical DB paths from
        :class:`~doge.config.settings.Settings` and returns a mapping of
        ``{db_filename: {table_name: row_count}}``. Missing databases are
        omitted.
        """
        ...

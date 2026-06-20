"""Repository implementations — bridge between ports and concrete databases.

These are the *adapters* in Ports & Adapters.  They implement the interfaces
defined in doge.core.ports.repository using DuckDB / SQLite.
"""

import sqlite3
from typing import List, Optional

from doge.config import get_settings
from doge.core.ports.repository import (
    IStockRepository,
    IReportRepository,
    ISchemaBrowser,
    INoteRepository,
    IStockNameRepository,
)
from .duckdb import DuckDBConnection
from .sqlite import SQLiteConnection, get_sqlite_stats


class DuckDBStockRepository(IStockRepository):
    """Stock data repository backed by DuckDB + attached SQLite.

    This adapter is **read-only** by design (single-logical-writer principle,
    ``market-data-storage.md:301``): DuckDB attaches the SQLite market files
    in read-only mode for analytical views. All writes MUST go through
    :class:`~doge.infrastructure.database.sqlite_storage.SQLiteStorageRepository`,
    which owns the live SQLite writer.
    """

    def __init__(self, conn: DuckDBConnection | None = None):
        self._conn = conn or DuckDBConnection(read_only=True)

    def ensure_schema(self, market: str) -> None:
        """Schema bootstrap is owned by ``SQLiteStorageRepository``.

        The DuckDB adapter is read-only (it attaches the SQLite market files
        read-only for analytical views). Calling this method indicates a
        caller-side wiring mistake — route schema bootstrap through
        :class:`~doge.infrastructure.database.sqlite_storage.SQLiteStorageRepository`
        instead.
        """
        raise NotImplementedError(
            "DuckDBStockRepository is read-only; initialize the schema via "
            "SQLiteStorageRepository.ensure_schema(market) instead."
        )

    def save_prices(self, market: str, frame) -> int:
        """Writes are owned by ``SQLiteStorageRepository``.

        The DuckDB adapter is read-only (it attaches the SQLite market files
        read-only for analytical views). Calling this method indicates a
        caller-side wiring mistake — route writes through
        :class:`~doge.infrastructure.database.sqlite_storage.SQLiteStorageRepository`
        instead.
        """
        raise NotImplementedError(
            "DuckDBStockRepository is read-only; persist prices via "
            "SQLiteStorageRepository.save_prices(market, frame) instead."
        )

    def get_prices(self, ticker: str, market: str, days: int = 20) -> List[dict]:
        if market == "cn":
            sql = """
                SELECT date, open, high, low, close, volume,
                       ROUND(return_pct, 2) AS ret_pct,
                       ma_5, ma_10, ma_20, ma_60,
                       ROUND(atr_14, 2) AS atr14,
                       ROUND(ma60_deviation, 2) AS ma60_dev,
                       ROUND(volatility_20d, 2) AS vol_20d
                FROM vw_daily_enriched_cn
                WHERE ticker = ?
                ORDER BY date DESC
                LIMIT ?
            """
        else:
            sql = """
                SELECT date, open, high, low, close, volume, amount
                FROM us.stock_prices
                WHERE ticker = ?
                ORDER BY date DESC
                LIMIT ?
            """
        df = self._conn.execute(sql, [ticker, days])
        return df.to_dict(orient="records")

    def get_kline(self, ticker: str, market: str, days: int = 120) -> List[dict]:
        """Return OHLCV + indicators in the legacy /api/data kline shape.

        The API contract expects ``atr_14`` (not ``atr14``) for CN and
        ``amount`` for US. We query the same analytical views as
        :meth:`get_prices` but select only the columns the router has always
        returned, then sort ascending by date.
        """
        if market == "cn":
            sql = """
                SELECT date, open, high, low, close, volume,
                       ma_5, ma_10, ma_20, ma_60,
                       ROUND(atr_14, 2) AS atr_14
                FROM vw_daily_enriched_cn
                WHERE ticker = ?
                ORDER BY date DESC
                LIMIT ?
            """
        else:
            sql = """
                SELECT date, open, high, low, close, volume, amount
                FROM us.stock_prices
                WHERE ticker = ?
                ORDER BY date DESC
                LIMIT ?
            """
        df = self._conn.execute(sql, [ticker, days])
        df = df.sort_values("date")
        return df.to_dict(orient="records")

    def get_overview(self, ticker: str, market: str) -> dict:
        from doge.infrastructure.cache.ticker_cache import JSONTickerNameCache
        settings = get_settings()

        # Name / sector
        cache = JSONTickerNameCache()
        name = cache.get(ticker)

        # Latest prices
        if market == "cn":
            prices_sql = """
                SELECT date, open, high, low, close, volume
                FROM cn.stock_prices
                WHERE ticker = ?
                ORDER BY date DESC
                LIMIT 10
            """
        else:
            prices_sql = """
                SELECT date, open, high, low, close, volume
                FROM us.stock_prices
                WHERE ticker = ?
                ORDER BY date DESC
                LIMIT 10
            """
        prices_df = self._conn.execute(prices_sql, [ticker])
        prices = prices_df.to_dict(orient="records")

        return {
            "ticker": ticker,
            "market": market,
            "name": name,
            "prices": prices,
        }

    def list_distinct_tickers(self, market: str) -> List[str]:
        """Return sorted distinct tickers from the market's ``stock_prices``.

        S005-009: replaces the direct ``SQLiteConnection(...).execute(
        "SELECT DISTINCT ticker FROM stock_prices")`` call that lived in the
        scan router. DuckDB attaches the cn/us SQLite files in read-only mode
        (see :class:`~doge.infrastructure.database.duckdb.DuckDBConnection`),
        so the query is ``SELECT DISTINCT ticker FROM <market>.stock_prices``
        against the same physical table the previous raw-SQL path read.

        Args:
            market: ``"cn"`` or ``"us"``. Any other value raises
                :class:`ValueError` rather than silently producing an empty
                list — the scan router validates ``market`` upstream, so an
                unexpected value here indicates a wiring bug.

        Returns:
            Sorted list of distinct ticker strings. ``[]`` when the attached
            database / table has no rows (fresh DB). DuckDB's
            ``ORDER BY ... NULLS LAST`` keeps results deterministic on
            databases with NULL ticker rows (defensive — the schema declares
            ``ticker`` as ``NOT NULL`` via the writer, but legacy DB files
            predate that constraint).
        """
        if market not in ("cn", "us"):
            raise ValueError(f"unknown market: {market!r} (expected 'cn' or 'us')")
        df = self._conn.execute(
            f"SELECT DISTINCT ticker FROM {market}.stock_prices "
            "WHERE ticker IS NOT NULL ORDER BY ticker"
        )
        # df may be empty; convert the single column to a plain list[str].
        if df.empty:
            return []
        return df["ticker"].astype(str).tolist()

    def get_sync_state(self, tickers: List[str]) -> dict[str, dict]:
        """Batch query {ticker: {"latest_date": str, "row_count": int}}."""
        if not tickers:
            return {}
        # Use the CN DB as proxy (all tickers tracked there)
        db_path = str(get_settings().db.cn_db)
        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()
            BATCH = 900
            result = {}
            for i in range(0, len(tickers), BATCH):
                batch = tickers[i:i + BATCH]
                placeholders = ",".join("?" * len(batch))
                sql = f"""
                    SELECT ticker, MAX(date) AS latest_date, COUNT(*) AS row_count
                    FROM stock_prices
                    WHERE ticker IN ({placeholders})
                    GROUP BY ticker
                """
                cur.execute(sql, batch)
                for row in cur.fetchall():
                    result[row[0]] = {"latest_date": row[1], "row_count": row[2]}
            for t in tickers:
                if t not in result:
                    result[t] = {"latest_date": None, "row_count": 0}
            return result
        finally:
            conn.close()


class SQLiteReportRepository(IReportRepository):
    """Research report / notes repository backed by SQLite."""

    def __init__(self, conn: SQLiteConnection | None = None):
        self._conn = conn or SQLiteConnection(use_row_factory=True)

    def list_macro_reports(self, limit: int = 100) -> List[dict]:
        rows = self._conn.execute(
            """SELECT id, date, timestamp, tags, analyst,
                      risk_signal, volatility
               FROM macro_reports
               ORDER BY date DESC, timestamp DESC
               LIMIT ?""",
            (limit,),
        )
        return [dict(r) for r in rows]

    def get_macro_report(self, report_id: int) -> Optional[dict]:
        row = self._conn.execute_one(
            "SELECT * FROM macro_reports WHERE id = ?", (report_id,)
        )
        return dict(row) if row else None

    def get_latest_macro_report(self) -> Optional[dict]:
        """Return the single most recent macro report, or ``None``."""
        row = self._conn.execute_one(
            "SELECT * FROM macro_reports ORDER BY date DESC, timestamp DESC LIMIT 1"
        )
        return dict(row) if row else None

    def save_macro_report(
        self, *, content: str, risk_signal: str,
        volatility: str, tags: str, analyst: str,
    ) -> None:
        from datetime import datetime
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        with self._conn.connect() as conn:
            conn.execute(
                """INSERT INTO macro_reports
                   (date, timestamp, tags, analyst, risk_signal, volatility, content)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (date_str, time_str, tags, analyst, risk_signal, volatility, content),
            )
            conn.commit()

    def save_research_report(
        self, *, title: str, content: str,
        tags: str, analyst: str,
    ) -> None:
        from datetime import datetime
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        with self._conn.connect() as conn:
            conn.execute(
                """INSERT INTO research_reports
                   (date, timestamp, tags, analyst, title, content)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (date_str, time_str, tags, analyst, title, content),
            )
            conn.commit()

    def list_research_reports(self, limit: int = 100) -> List[dict]:
        """List research reports ordered newest-first."""
        rows = self._conn.execute(
            """SELECT id, date, timestamp, tags, analyst, title
               FROM research_reports
               ORDER BY date DESC, timestamp DESC
               LIMIT ?""",
            (limit,),
        )
        return [dict(r) for r in rows]

    def get_research_report(self, report_id: int) -> Optional[dict]:
        """Fetch a single research report by id, or ``None``."""
        row = self._conn.execute_one(
            "SELECT * FROM research_reports WHERE id = ?", (report_id,)
        )
        return dict(row) if row else None

    def add_note(
        self, *, ticker: str, content: str, market: str,
        note_type: str, title: Optional[str],
        tags: Optional[str], price_at_note: Optional[float],
        source: Optional[str],
    ) -> int:
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._conn.connect() as conn:
            cur = conn.execute(
                """INSERT INTO stock_notes
                   (ticker, market, created_at, note_type, title, content, tags, price_at_note, source)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (ticker, market, now, note_type, title, content, tags, price_at_note, source),
            )
            conn.commit()
            return cur.lastrowid

    def search_notes(self, query: str, limit: int = 50) -> List[dict]:
        pattern = f"%{query}%"
        rows = self._conn.execute(
            """SELECT * FROM stock_notes
               WHERE ticker LIKE ? OR content LIKE ? OR title LIKE ?
               ORDER BY created_at DESC
               LIMIT ?""",
            (pattern, pattern, pattern, limit),
        )
        return [dict(r) for r in rows]

    def list_stock_names(self) -> List[dict]:
        rows = self._conn.execute(
            "SELECT ticker, name_cn, sector FROM stock_names"
        )
        return [dict(r) for r in rows]


class SQLiteStockNameRepository(IStockNameRepository):
    """Stock-name cache repository backed by SQLite.

    Persists ticker metadata (name, sector) to the ``stock_names`` table in the
    research database. This is a separate domain from notes, so it implements
    its own port (S007-004).
    """

    def __init__(self, conn: SQLiteConnection | None = None):
        self._conn = conn or SQLiteConnection(use_row_factory=True)

    def get_existing_names(self) -> dict[str, str]:
        """Return ``{ticker: name_cn}`` for all cached names."""
        try:
            rows = self._conn.execute(
                "SELECT ticker, name_cn FROM stock_names"
            )
            return {r["ticker"]: (r["name_cn"] or "") for r in rows}
        except sqlite3.OperationalError:
            # stock_names table may not exist on fresh/legacy DBs.
            return {}

    def save_name(
        self,
        ticker: str,
        name_cn: str,
        name_en: Optional[str] = None,
        market: str = "cn",
        sector: Optional[str] = None,
        industry: Optional[str] = None,
    ) -> None:
        """Persist or update a stock name record."""
        from datetime import datetime

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._conn.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO stock_names
                (ticker, name_cn, name_en, market, sector, industry, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (ticker, name_cn, name_en or "", market, sector or "", industry or "", now),
            )
            conn.commit()

    def list_stock_names(self) -> List[dict]:
        """Return all cached stock-name records."""
        try:
            rows = self._conn.execute(
                "SELECT ticker, name_cn, sector FROM stock_names"
            )
            return [dict(r) for r in rows]
        except sqlite3.OperationalError:
            return []


class SQLiteSchemaBrowser(ISchemaBrowser):
    """Schema-introspection adapter backed by SQLiteConnection.

    This adapter implements the generic table-browsing surface the API data
    router exposes. It resolves DB paths from centralized settings and uses
    the existing :class:`~doge.infrastructure.database.sqlite.SQLiteConnection`
    adapter so no raw ``sqlite3.connect`` leaks into the interface layer.
    """

    _MARKET_TO_PATH_ATTR = {
        "cn": "cn_db",
        "us": "us_db",
        "research": "research_db",
    }

    def __init__(self):
        self._settings = get_settings()

    def _db_path(self, market: str) -> str:
        if market not in self._MARKET_TO_PATH_ATTR:
            raise ValueError(f"unknown market: {market}")
        return str(getattr(self._settings.db, self._MARKET_TO_PATH_ATTR[market]))

    def list_tables(self, market: str) -> List[str]:
        """Return sorted table names for ``market``; missing DB returns []."""
        import os

        db_path = self._db_path(market)
        if not os.path.exists(db_path):
            return []
        conn = SQLiteConnection(db_path)
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        return [r[0] for r in rows]

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
        import os

        db_path = self._db_path(market)
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"database not found: {db_path}")

        conn = SQLiteConnection(db_path, use_row_factory=True)
        with conn.connect() as cursor_conn:
            cur = cursor_conn.cursor()
            # Validate table exists
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,),
            )
            if not cur.fetchone():
                raise FileNotFoundError(f"table '{table_name}' not found")

            # Column list
            cur.execute(f"PRAGMA table_info([{table_name}])")
            columns = [r[1] for r in cur.fetchall()]

            # Build WHERE / params
            where = ""
            params: List[object] = []
            if search and columns:
                conditions = " OR ".join(
                    [f"CAST([{col}] AS TEXT) LIKE ?" for col in columns[:5]]
                )
                where = f"WHERE {conditions}"
                params = [f"%{search}%"] * min(5, len(columns))

            # Total count
            cur.execute(f"SELECT COUNT(*) FROM [{table_name}] {where}", params)
            total = cur.fetchone()[0]

            # Order
            order = ""
            if sort_by and sort_by in columns:
                direction = "DESC" if sort_order == "desc" else "ASC"
                order = f"ORDER BY [{sort_by}] {direction}"
            elif "date" in columns and "ticker" in columns:
                order = "ORDER BY date DESC, ticker ASC"

            # Page
            offset = (page - 1) * page_size
            cur.execute(
                f"SELECT * FROM [{table_name}] {where} {order} LIMIT ? OFFSET ?",
                params + [page_size, offset],
            )
            rows = [dict(r) for r in cur.fetchall()]

        return {
            "columns": columns,
            "rows": rows,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def database_stats(self) -> dict:
        """Return row counts per table for all configured databases."""
        import os

        result = {}
        for market, attr in self._MARKET_TO_PATH_ATTR.items():
            db_path = str(getattr(self._settings.db, attr))
            db_name = os.path.basename(db_path)
            if not os.path.exists(db_path):
                continue
            conn = SQLiteConnection(db_path)
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            db_stats = {}
            for (table_name,) in tables:
                count = conn.execute_scalar(f"SELECT COUNT(*) FROM [{table_name}]")
                db_stats[table_name] = count
            result[db_name] = db_stats
        return result

    def get_sqlite_stats(self, market: str) -> dict:
        """Return detailed per-table statistics for ``market``."""
        db_path = self._db_path(market)
        return get_sqlite_stats(db_path)


class SQLiteNoteRepository(INoteRepository):
    """Stock note repository backed by SQLite with soft-delete support.

    Uses :class:`~doge.infrastructure.database.sqlite.SQLiteConnection` for
    all database access — no raw ``sqlite3.connect`` calls. The soft-delete
    behavior (``deleted_at`` column) mirrors the legacy
    ``src/ai_analysis/stock_notes.py`` contract: reads exclude rows where
    ``deleted_at IS NOT NULL`` unless explicitly requested.
    """

    def __init__(self, conn: SQLiteConnection | None = None):
        self._conn = conn or SQLiteConnection(use_row_factory=True)

    # ------------------------------------------------------------------
    # Schema helpers
    # ------------------------------------------------------------------
    def _ensure_note_schema(self) -> None:
        """Create the minimal stock-notes schema on a fresh local DB.

        The app treats an empty ``research_insights.db`` as a valid fresh
        checkout. Creating an empty notes table preserves that contract while
        still allowing read paths to return 404/[] instead of leaking a raw
        ``sqlite3.OperationalError`` through the API.
        """
        with self._conn.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS stock_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    market TEXT DEFAULT 'cn',
                    created_at TEXT NOT NULL,
                    note_type TEXT DEFAULT 'comment',
                    title TEXT,
                    content TEXT NOT NULL,
                    tags TEXT,
                    price_at_note REAL,
                    source TEXT,
                    sentiment TEXT,
                    deleted_at TIMESTAMP
                )
                """
            )
            conn.commit()

    def _ensure_deleted_at_column(self) -> None:
        """Idempotently add the ``deleted_at`` column for soft-delete support.

        Safe to call on any DB: issues ``PRAGMA table_info`` first and only
        runs ``ALTER TABLE ... ADD COLUMN`` when the column is missing.
        """
        self._ensure_note_schema()
        try:
            rows = self._conn.execute("PRAGMA table_info(stock_notes)")
            existing = {r[1] for r in rows}
            if "deleted_at" not in existing:
                with self._conn.connect() as conn:
                    conn.execute(
                        "ALTER TABLE stock_notes ADD COLUMN deleted_at TIMESTAMP"
                    )
                    conn.commit()
        except sqlite3.OperationalError:
            # Defensive fallback for malformed fixtures; the schema bootstrap
            # above already handles normal fresh local DBs.
            pass

    # ------------------------------------------------------------------
    # INoteRepository implementation
    # ------------------------------------------------------------------
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
        """Persist a new note and return its id.

        Dynamically detects available columns via ``PRAGMA table_info`` so
        the INSERT works on both the full schema (with ``sentiment``) and
        legacy schemas (without it). This preserves backward compatibility
        with existing DB files that predate the ``sentiment`` column.
        """
        from datetime import datetime

        now = datetime.now().isoformat(sep=" ", timespec="microseconds")

        # Build INSERT dynamically based on existing columns (legacy-safe)
        self._ensure_deleted_at_column()
        rows = self._conn.execute("PRAGMA table_info(stock_notes)")
        existing_cols = {r[1] for r in rows}

        field_values = {
            "ticker": ticker,
            "market": market,
            "created_at": now,
            "note_type": note_type,
            "title": title,
            "content": note_text,
            "tags": tags,
            "price_at_note": price_at_note,
            "source": source,
            "sentiment": sentiment,
        }
        # Only include fields whose columns exist in the table
        present = {k: v for k, v in field_values.items() if k in existing_cols}
        cols = ", ".join(present.keys())
        placeholders = ", ".join("?" * len(present))
        values = list(present.values())

        with self._conn.connect() as conn:
            cur = conn.execute(
                f"INSERT INTO stock_notes ({cols}) VALUES ({placeholders})",
                values,
            )
            conn.commit()
            return cur.lastrowid

    def delete_note(self, note_id: int) -> bool:
        """Soft-delete a note by id. Returns ``True`` if a row was affected."""
        from datetime import datetime

        self._ensure_deleted_at_column()
        now = datetime.now().isoformat(sep=" ", timespec="microseconds")
        with self._conn.connect() as conn:
            cur = conn.execute(
                "UPDATE stock_notes SET deleted_at = ? "
                "WHERE id = ? AND deleted_at IS NULL",
                (now, note_id),
            )
            conn.commit()
            return cur.rowcount > 0

    def get_notes(
        self,
        ticker: Optional[str] = None,
        include_deleted: bool = False,
        limit: Optional[int] = None,
        days_back: Optional[int] = None,
        note_type: Optional[str] = None,
    ) -> List[dict]:
        """Return notes with optional filters (ticker, date window, type, limit)."""
        self._ensure_deleted_at_column()
        sql = "SELECT * FROM stock_notes WHERE 1=1"
        params: List[object] = []
        if ticker:
            sql += " AND ticker = ?"
            params.append(ticker)
        if not include_deleted:
            sql += " AND deleted_at IS NULL"
        if note_type:
            sql += " AND note_type = ?"
            params.append(note_type)
        if days_back:
            from datetime import datetime, timedelta
            cutoff = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
            sql += " AND created_at >= ?"
            params.append(cutoff)
        sql += " ORDER BY created_at DESC"
        if limit:
            sql += " LIMIT ?"
            params.append(limit)
        rows = self._conn.execute(sql, params)
        return [dict(r) for r in rows]

    def search_notes(self, keyword: str, limit: int = 50) -> List[dict]:
        """Search note content and title (soft-deleted excluded)."""
        self._ensure_deleted_at_column()
        pattern = f"%{keyword}%"
        rows = self._conn.execute(
            """SELECT ticker, created_at, note_type, title, content
               FROM stock_notes
               WHERE (content LIKE ? OR title LIKE ?) AND deleted_at IS NULL
               ORDER BY created_at DESC
               LIMIT ?""",
            (pattern, pattern, limit),
        )
        return [dict(r) for r in rows]

    def get_recent_notes(self, days: int = 7, limit: int = 100) -> List[dict]:
        """Return the most recent notes within a date window."""
        self._ensure_deleted_at_column()
        from datetime import datetime, timedelta
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = self._conn.execute(
            """SELECT ticker, market, created_at, note_type, title, content, tags
               FROM stock_notes
               WHERE created_at >= ? AND deleted_at IS NULL
               ORDER BY created_at DESC
               LIMIT ?""",
            (cutoff, limit),
        )
        return [dict(r) for r in rows]

    def list_tracked_tickers(self) -> List[dict]:
        """Return tickers with active notes and their metadata."""
        self._ensure_deleted_at_column()
        rows = self._conn.execute(
            """SELECT ticker, market, COUNT(*) AS n, MAX(created_at) AS last_note
               FROM stock_notes WHERE deleted_at IS NULL
               GROUP BY ticker, market
               ORDER BY last_note DESC"""
        )
        return [dict(r) for r in rows]

    def get_ticker_with_context(self, ticker: str, market: str = "cn") -> dict:
        """Return composite view: name/sector from stock_names + notes + prices.

        Mirrors the legacy ``src/ai_analysis/stock_notes.py`` response shape
        including ``price_data`` from DuckDB and ``name_cn`` / ``name_en``
        / ``sector`` / ``industry`` from ``stock_names``.

        Error semantics (S004 Wave A / ADR-0007 envelope contract): the
        DuckDB price block is BEST-EFFORT — if the price DB is unavailable
        ``price_data`` stays ``None`` and no exception is raised (mirrors
        legacy best-effort intent and keeps tests with no DuckDB file
        working). All other blocks (name lookup, notes count + select)
        PROPAGATE their exceptions so the global
        ``@app.exception_handler(Exception)`` in ``src/api/main.py`` can
        shape them into the stable ``{"error": {"code": "internal_error",
        "message": "internal server error"}}`` envelope — the previously
        ``except Exception`` swallows that stuffed errors into
        ``price_error`` / ``notes_error`` keys were a parity regression
        (the contract tests in ``tests/contract/test_api_error_envelope.py``
        pin the propagating behavior).
        """
        self._ensure_deleted_at_column()
        result: dict = {
            "ticker": ticker,
            "market": market,
            "name_cn": None,
            "name_en": None,
            "sector": None,
            "industry": None,
            "price_data": None,
            "notes": [],
            "note_count_total": 0,
        }

        # 0. Name / sector / industry from stock_names. The table may simply be
        #    absent (fresh DB / test fixture) — that is benign and leaves the
        #    name fields None; genuine (non-OperationalError) faults propagate.
        try:
            row = self._conn.execute_one(
                "SELECT name_cn, name_en, sector, industry FROM stock_names WHERE ticker = ?",
                (ticker,),
            )
            if row:
                result["name_cn"] = row["name_cn"] if hasattr(row, "keys") else row[0]
                result["name_en"] = row["name_en"] if hasattr(row, "keys") else row[1]
                result["sector"] = row["sector"] if hasattr(row, "keys") else row[2]
                result["industry"] = row["industry"] if hasattr(row, "keys") else row[3]
        except sqlite3.OperationalError:
            # stock_names table absent (fresh DB / test fixture) — benign.
            pass

        # 1. Price data from DuckDB (BEST-EFFORT: stays None if DuckDB / the
        #    price SQLite file is unavailable — do NOT raise).
        try:
            from doge.infrastructure.database.duckdb import DuckDBConnection
            from doge.config import get_settings

            settings = get_settings()
            db_label = "cn" if market == "cn" else "us"
            price_db_path = str(
                settings.db.cn_db if db_label == "cn" else settings.db.us_db
            ).replace("\\", "/")

            # DuckDBConnection exposes a ``connect()`` context manager that
            # yields a configured ``duckdb.DuckDBPyConnection`` (auto-attaches
            # cn/us SQLite, closes on exit). The previous code used a
            # non-existent ``con._conn`` attribute, which only worked because
            # the surrounding ``try/except Exception`` swallowed the
            # ``AttributeError``.
            with DuckDBConnection(read_only=True).connect() as con:
                con.execute(
                    "ATTACH IF NOT EXISTS '{}' AS {} (TYPE sqlite)".format(
                        price_db_path, db_label
                    )
                )
                price_df = con.execute(
                    """SELECT date, open, high, low, close, volume, amount
                       FROM {}.stock_prices
                       WHERE ticker = ?
                       ORDER BY date DESC""".format(db_label),
                    [ticker],
                ).df()
            if not price_df.empty:
                result["price_data"] = price_df.to_dict(orient="records")
        except Exception:
            # Best-effort parity with legacy: if DuckDB / the price DB is
            # unavailable (e.g. fresh test fixture with no DuckDB file),
            # leave ``price_data`` as None and do NOT raise.
            pass

        # 2. Note count and notes (SQLite, soft-deleted excluded — errors
        #    PROPAGATE to the global exception handler for envelope shaping).
        count_row = self._conn.execute_one(
            "SELECT COUNT(*) FROM stock_notes WHERE ticker = ? AND deleted_at IS NULL",
            (ticker,),
        )
        if count_row:
            result["note_count_total"] = count_row[0] if not hasattr(count_row, "keys") else count_row["COUNT(*)"]

        rows = self._conn.execute(
            """SELECT id, created_at, note_type, title, content, tags, price_at_note, source
               FROM stock_notes
               WHERE ticker = ? AND deleted_at IS NULL
               ORDER BY created_at DESC LIMIT 20""",
            (ticker,),
        )
        result["notes"] = [dict(r) for r in rows]

        return result

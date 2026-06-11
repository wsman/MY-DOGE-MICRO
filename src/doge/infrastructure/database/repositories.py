"""Repository implementations — bridge between ports and concrete databases.

These are the *adapters* in Ports & Adapters.  They implement the interfaces
defined in doge.core.ports.repository using DuckDB / SQLite.
"""

import sqlite3
from typing import List, Optional

from doge.config import get_settings
from doge.core.ports.repository import IStockRepository, IReportRepository
from .duckdb import DuckDBConnection
from .sqlite import SQLiteConnection


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

"""SQLite connection adapter with context-manager support.

Replaces scattered `sqlite3.connect()` calls in routers and analysis modules.
"""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from doge.config import get_settings


def get_sqlite_stats(db_path: Path | str) -> dict:
    """Return per-table statistics for a SQLite database.

    Mirrors the legacy ``src/ai_analysis/__init__.py::get_sqlite_stats`` shape:

    Returns:
        ``{"table_name": {"row_count": int, "columns": [...],
        "date_range": [...]|None, "distinct_tickers": int|None}}``.
    """
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {}
        for (tname,) in cur.fetchall():
            cur.execute(f"SELECT COUNT(*) FROM [{tname}]")
            row_count = cur.fetchone()[0]
            cur.execute(f"PRAGMA table_info([{tname}])")
            columns = [
                {"name": c[1], "type": c[2], "nullable": not c[3]}
                for c in cur.fetchall()
            ]
            date_range = None
            ticker_count = None
            if tname == "stock_prices" and row_count > 0:
                cur.execute(f"SELECT MIN(date), MAX(date) FROM [{tname}]")
                date_range = list(cur.fetchone())
                cur.execute(f"SELECT COUNT(DISTINCT ticker) FROM [{tname}]")
                ticker_count = cur.fetchone()[0]
            tables[tname] = {
                "row_count": row_count,
                "columns": columns,
                "date_range": date_range,
                "distinct_tickers": ticker_count,
            }
        return tables
    finally:
        conn.close()


class SQLiteConnection:
    """SQLite connection manager with row factory support."""

    def __init__(self, db_path: Path | str | None = None, use_row_factory: bool = False):
        self._settings = get_settings()
        self._db_path = db_path
        self._use_row_factory = use_row_factory

    def _resolve_path(self) -> str:
        if self._db_path is not None:
            return str(self._db_path)
        return str(self._settings.db.research_db)

    @contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Yield a configured SQLite connection."""
        conn = sqlite3.connect(self._resolve_path())
        if self._use_row_factory:
            conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def execute(self, sql: str, params=()) -> list[sqlite3.Row] | list[tuple]:
        """Execute query and return all rows."""
        with self.connect() as conn:
            cur = conn.execute(sql, params)
            return cur.fetchall()

    def execute_one(self, sql: str, params=()) -> sqlite3.Row | tuple | None:
        """Execute query and return first row, or None."""
        with self.connect() as conn:
            cur = conn.execute(sql, params)
            return cur.fetchone()

    def execute_scalar(self, sql: str, params=()):
        """Execute query and return first column of first row."""
        row = self.execute_one(sql, params)
        return row[0] if row else None

"""SQLite connection adapter with context-manager support.

Replaces scattered `sqlite3.connect()` calls in routers and analysis modules.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from doge.config import get_settings


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

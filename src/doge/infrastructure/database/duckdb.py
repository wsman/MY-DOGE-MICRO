"""DuckDB connection adapter — centralized, reusable, configurable.

Replaces scattered `connect_duckdb()` and `get_duckdb_connection()`
calls across ai_analysis, cli, api, mcp_server.
"""

import os
from contextlib import contextmanager
from typing import Generator

import duckdb

from doge.config import get_settings

# Limit OpenBLAS threads to avoid OOM during pandas conversion
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")


class DuckDBConnection:
    """DuckDB connection manager with automatic SQLite attachment."""

    def __init__(self, read_only: bool = True):
        self._settings = get_settings()
        self._read_only = read_only
        self._duckdb_path = str(self._settings.db.duckdb)
        self._cn_db = self._settings.db.cn_db.as_posix()
        self._us_db = self._settings.db.us_db.as_posix()

    @contextmanager
    def connect(self) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        """Yield a configured DuckDB connection.

        Automatically attaches cn/us SQLite databases.
        Connection is closed on exit.
        """
        con = duckdb.connect(self._duckdb_path, read_only=self._read_only)
        try:
            con.execute("SET threads=4")
            read_only_flag = "READ_ONLY" if self._read_only else ""
            con.execute(
                f"ATTACH IF NOT EXISTS '{self._cn_db}' AS cn (TYPE sqlite{',' + read_only_flag if read_only_flag else ''})"
            )
            con.execute(
                f"ATTACH IF NOT EXISTS '{self._us_db}' AS us (TYPE sqlite{',' + read_only_flag if read_only_flag else ''})"
            )
            yield con
        finally:
            con.close()

    def execute(self, sql: str, params=None):
        """Execute a query and return a DataFrame (convenience)."""
        with self.connect() as con:
            if params:
                return con.execute(sql, params).df()
            return con.execute(sql).df()

    def refresh_views(self, con: duckdb.DuckDBPyConnection | None = None) -> None:
        """Execute views.sql to refresh all DuckDB views."""
        close_on_exit = False
        if con is None:
            # Need write access for CREATE OR REPLACE VIEW
            con = duckdb.connect(self._duckdb_path, read_only=False)
            close_on_exit = True
            con.execute(f"ATTACH IF NOT EXISTS '{self._cn_db}' AS cn (TYPE sqlite)")
            con.execute(f"ATTACH IF NOT EXISTS '{self._us_db}' AS us (TYPE sqlite)")

        try:
            views_sql_path = self._settings.db.views_sql
            if not views_sql_path.exists():
                return
            with open(views_sql_path, "r", encoding="utf-8") as f:
                sql = f.read()
            for stmt in sql.split(";"):
                stmt = stmt.strip()
                if stmt and not stmt.startswith("--"):
                    try:
                        con.execute(stmt)
                    except Exception:
                        pass  # Best-effort; individual views may fail
        finally:
            if close_on_exit:
                con.close()


# Legacy compatibility — will be removed after full migration
@contextmanager
def get_duckdb_connection(read_only: bool = True):
    """Legacy wrapper.  Prefer DuckDBConnection().connect()."""
    conn = DuckDBConnection(read_only=read_only)
    yield from conn.connect()


def connect_duckdb(read_only: bool = False):
    """Legacy wrapper.  Prefer DuckDBConnection().connect()."""
    return DuckDBConnection(read_only=read_only)

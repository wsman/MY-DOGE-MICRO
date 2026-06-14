"""DuckDB connection adapter — centralized, reusable, configurable.

Replaces scattered `connect_duckdb()` and `get_duckdb_connection()`
calls across ai_analysis, cli, api, mcp_server.
"""

import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

import duckdb

from doge.config import get_settings

logger = logging.getLogger(__name__)

# Limit OpenBLAS threads to avoid OOM during pandas conversion
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")


def _strip_sql_comments(sql_text: str) -> str:
    """Remove full-line and trailing ``--`` comments before statement splitting.

    S003-005: the version-controlled ``views.sql`` carries a multi-paragraph
    header comment whose prose contains semicolons (e.g. "sign convention; the
    downstream ..."). The naive ``sql.split(';')`` used by the refresh path
    breaks such prose into fragments that don't start with ``--`` and then fail
    to parse as SQL — and worse, can absorb a real statement into a comment
    fragment so the view never updates. Stripping full-line and trailing inline
    comments before splitting (mirrors the test helpers
    ``tests/migration/test_retention_view_window_safety.py::_strip_sql_comments``
    and ``tests/migration/test_rsrs_view_sign_convention.py``) makes the refresh
    robust to comment content. The DDL has no ``--`` inside string literals, so
    the naive split-on-``--`` is safe here.
    """
    cleaned_lines = []
    for line in sql_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue  # drop full-line comments
        if "--" in line:
            line = line.split("--", 1)[0]  # drop trailing inline comments
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


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
        """Execute the canonical ``views.sql`` to refresh all DuckDB views.

        Resolves the DDL via ``DBConfig.resolved_views_sql()`` (S003-005): the
        version-controlled copy at
        ``src/doge/infrastructure/database/views.sql`` is preferred; the
        data-dir mirror ``data/views.sql`` is the backward-compat fallback.
        """
        close_on_exit = False
        if con is None:
            # Need write access for CREATE OR REPLACE VIEW
            con = duckdb.connect(self._duckdb_path, read_only=False)
            close_on_exit = True
            con.execute(f"ATTACH IF NOT EXISTS '{self._cn_db}' AS cn (TYPE sqlite)")
            con.execute(f"ATTACH IF NOT EXISTS '{self._us_db}' AS us (TYPE sqlite)")

        try:
            views_sql_path = self._settings.db.resolved_views_sql()
            if not views_sql_path.exists():
                return
            with open(views_sql_path, "r", encoding="utf-8") as f:
                sql = f.read()
            sql = _strip_sql_comments(sql)
            for stmt in sql.split(";"):
                stmt = stmt.strip()
                if stmt:
                    try:
                        con.execute(stmt)
                    except Exception:
                        pass  # Best-effort; individual views may fail
        finally:
            if close_on_exit:
                con.close()

    def query_view(self, view_name: str, limit: Optional[int] = None):
        """Query a named DuckDB view and return a DataFrame.

        Args:
            view_name: DuckDB view or table identifier.
            limit: Optional row limit.
        """
        sql = f"SELECT * FROM {view_name}"
        if limit:
            sql += f" LIMIT {limit}"
        return self.execute(sql)

    def query_sql(self, sql: str, params=None):
        """Execute an arbitrary SQL query and return a DataFrame."""
        return self.execute(sql, params)

    def get_duckdb_view_stats(self, con: Optional[duckdb.DuckDBPyConnection] = None) -> dict:
        """Return {view_name: {"row_count": int|None}} for all DuckDB views.

        If ``con`` is provided it is used as-is (caller manages lifecycle);
        otherwise a temporary read-only connection is opened.
        """
        close_on_exit = False
        if con is None:
            con = duckdb.connect(self._duckdb_path, read_only=True)
            close_on_exit = True
            con.execute(f"ATTACH IF NOT EXISTS '{self._cn_db}' AS cn (TYPE sqlite, READ_ONLY)")
            con.execute(f"ATTACH IF NOT EXISTS '{self._us_db}' AS us (TYPE sqlite, READ_ONLY)")

        try:
            views = {}
            result = con.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_type='VIEW'"
            ).fetchall()
            for (vname,) in result:
                try:
                    cnt = con.execute(f"SELECT COUNT(*) FROM {vname}").fetchone()[0]
                    views[vname] = {"row_count": cnt}
                except Exception:
                    views[vname] = {"row_count": None}
            return views
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

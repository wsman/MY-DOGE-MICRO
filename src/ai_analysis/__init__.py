"""Deprecated AI-analysis package root — forwards to canonical helpers.

``src/ai_analysis`` is kept as a backwards-compatible shim for Sprint 007.
The canonical implementations now live in:

- ``doge.infrastructure.database.duckdb`` — DuckDB connection/query helpers
- ``doge.infrastructure.database.sqlite`` — SQLite stats helper
- ``doge.core.utils`` — ``normalize_ticker``
- ``doge.config.settings`` — database/report directory paths

This module re-exports the legacy symbols so existing scripts and tests keep
working. It will be removed in Sprint 008.
"""
import warnings
from contextlib import contextmanager as _contextmanager
from typing import Optional

warnings.warn(
    "ai_analysis is deprecated; use doge.infrastructure.database and "
    "doge.application.use_cases instead",
    DeprecationWarning,
    stacklevel=2,
)

from doge.config import get_settings
from doge.core.utils import normalize_ticker
from doge.infrastructure.database.duckdb import DuckDBConnection
from doge.infrastructure.database.sqlite import get_sqlite_stats


# ── Lazy path constants (resolved at access time so tests can override env) ──
_CONSTANT_MAP = {
    "DB_DIR": lambda s: s.db.dir,
    "CN_DB": lambda s: s.db.cn_db,
    "US_DB": lambda s: s.db.us_db,
    "RESEARCH_DB": lambda s: s.db.research_db,
    "DUCKDB_PATH": lambda s: s.db.duckdb,
    "VIEWS_SQL": lambda s: s.db.views_sql,
    "VIEWS_SQL_TRACKED": lambda s: s.db.views_sql_tracked,
    "REPORT_DIR": lambda s: s.report_dir,
}


def __getattr__(name: str):
    if name in _CONSTANT_MAP:
        return _CONSTANT_MAP[name](get_settings())
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# ── DuckDB helpers ──
def connect_duckdb(read_only: bool = False):
    """Legacy wrapper. Prefer ``DuckDBConnection``."""
    return DuckDBConnection(read_only=read_only)


@_contextmanager
def get_duckdb_connection(read_only: bool = True):
    """Legacy context manager. Prefer ``DuckDBConnection(read_only).connect()``"."""
    conn = DuckDBConnection(read_only=read_only)
    yield from conn.connect()


def run_views_sql(con=None) -> None:
    """Legacy view refresh. Prefer ``DuckDBConnection().refresh_views()``."""
    DuckDBConnection(read_only=False).refresh_views(con)


def query_view(view_name, limit: Optional[int] = None):
    """Legacy view query. Prefer ``DuckDBConnection().query_view()``."""
    return DuckDBConnection(read_only=True).query_view(view_name, limit=limit)


def query_sql(sql, params=None):
    """Legacy SQL query. Prefer ``DuckDBConnection().query_sql()``."""
    return DuckDBConnection(read_only=True).query_sql(sql, params)


# get_duckdb_view_stats already mirrored by DuckDBConnection
get_duckdb_view_stats = DuckDBConnection(read_only=True).get_duckdb_view_stats


# ── Report dir helper ──
def ensure_report_dir() -> None:
    """Legacy helper. Equivalent to ``get_settings().report_dir.mkdir(...)``."""
    get_settings().report_dir.mkdir(parents=True, exist_ok=True)


# ── Public re-exports ──
__all__ = [
    "normalize_ticker",
    "connect_duckdb",
    "get_duckdb_connection",
    "run_views_sql",
    "query_view",
    "query_sql",
    "get_sqlite_stats",
    "get_duckdb_view_stats",
    "ensure_report_dir",
]

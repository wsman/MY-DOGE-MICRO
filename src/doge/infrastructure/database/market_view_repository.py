"""DuckDB market-view repository adapter.

Implements :class:`~doge.core.ports.market_view.IMarketViewRepository` by
wrapping a read-only :class:`~doge.infrastructure.database.duckdb.DuckDBConnection`
and delegating ``execute`` to it. This is the single infrastructure adapter the
four read-only view-backed services depend on (via the port), per ADR-0010.

The adapter is intentionally thin: it owns no SQL — the concrete view queries
live in the services that consume it.
"""

from typing import Optional

import pandas as pd

from doge.core.ports.market_view import IMarketViewRepository
from .duckdb import DuckDBConnection


class DuckDBMarketViewRepository(IMarketViewRepository):
    """Read-only DuckDB view execution handle for the view-backed services."""

    def __init__(self, conn: Optional[DuckDBConnection] = None, read_only: bool = True):
        """Create the repository.

        Args:
            conn: An existing ``DuckDBConnection`` to wrap (e.g. for sharing or
                testing). When ``None``, a new read-only connection is built.
            read_only: Forwarded to ``DuckDBConnection`` when *conn* is ``None``.
                View-backed services are read-only by design.
        """
        self._conn = conn if conn is not None else DuckDBConnection(read_only=read_only)

    def execute(self, sql: str, params: Optional[list] = None) -> pd.DataFrame:
        """Execute *sql* and return the result as a DataFrame.

        Delegates to the wrapped ``DuckDBConnection.execute`` (which opens a
        read-only connection, binds *params* when present, and returns a
        DataFrame).
        """
        return self._conn.execute(sql, params)

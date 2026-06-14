"""Abstract market-view repository port (read-only DuckDB view execution).

Captures the narrow ``execute(sql, params) -> DataFrame`` surface the four
read-only view-backed services (Ranking/Breadth/Anomaly/View) need. It is the
single method that lets these services depend on a port instead of the concrete
``DuckDBConnection`` adapter, satisfying clean-architecture-migration AC-2 /
AC-9. See ADR-0010 for the port-injection decision.
"""

from abc import ABC, abstractmethod
from typing import Optional

import pandas as pd


class IMarketViewRepository(ABC):
    """Read-only execution handle over the DuckDB analytical views.

    Implementations wrap a read-only DuckDB connection and delegate ``execute``
    to the underlying connection. Concrete SQL is owned by the *services*, not
    by this adapter, so the port stays a thin execution surface.
    """

    @abstractmethod
    def execute(self, sql: str, params: Optional[list] = None) -> pd.DataFrame:
        """Execute *sql* (optionally parameterized) and return a DataFrame.

        Args:
            sql: A read-only SQL statement (typically against a ``vw_*`` view).
            params: Optional bind parameters forwarded to the connection.

        Returns:
            The query result as a :class:`pandas.DataFrame`.
        """
        ...

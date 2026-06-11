"""Market breadth service."""

from typing import List

from doge.infrastructure.database.duckdb import DuckDBConnection


class BreadthService:
    """Market breadth queries."""

    def __init__(self, conn: DuckDBConnection | None = None):
        self._conn = conn or DuckDBConnection(read_only=True)

    def breadth(self, market: str = "cn", days: int = 10) -> List[dict]:
        view = f"vw_market_breadth_{market}"
        df = self._conn.execute(f"SELECT * FROM {view} LIMIT ?", [days])
        return df.to_dict(orient="records")

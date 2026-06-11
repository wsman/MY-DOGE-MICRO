"""RSRS ranking service."""

from typing import List

from doge.infrastructure.database.duckdb import DuckDBConnection


class RankingService:
    """RSRS momentum ranking queries."""

    def __init__(self, conn: DuckDBConnection | None = None):
        self._conn = conn or DuckDBConnection(read_only=True)

    def rsrs(self, market: str = "cn", top: int = 20) -> List[dict]:
        view = f"vw_rsrs_ranking_{market}"
        df = self._conn.execute(f"SELECT * FROM {view} LIMIT ?", [top])
        return df.to_dict(orient="records")

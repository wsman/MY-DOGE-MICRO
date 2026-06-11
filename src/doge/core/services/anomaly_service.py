"""Volume anomaly service."""

from typing import List

from doge.infrastructure.database.duckdb import DuckDBConnection


class AnomalyService:
    """Volume anomaly queries."""

    def __init__(self, conn: DuckDBConnection | None = None):
        self._conn = conn or DuckDBConnection(read_only=True)

    def anomalies(self, min_ratio: float = 3.0, top: int = 20) -> List[dict]:
        df = self._conn.execute("""
            SELECT ticker, date, volume, ROUND(avg_vol_20d, 0) AS avg_vol,
                   ROUND(vol_ratio, 2) AS vol_ratio,
                   ROUND(intraday_return, 2) AS ret_pct
            FROM vw_volume_anomalies_cn
            WHERE vol_ratio >= ?
            ORDER BY vol_ratio DESC
            LIMIT ?
        """, [min_ratio, top])
        return df.to_dict(orient="records")

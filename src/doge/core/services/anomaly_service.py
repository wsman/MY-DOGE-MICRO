"""Volume anomaly service."""

from typing import List

from doge.core.ports.market_view import IMarketViewRepository


class AnomalyService:
    """Volume anomaly queries.

    Depends on the :class:`~doge.core.ports.market_view.IMarketViewRepository`
    port (per ADR-0010); this service imports no infrastructure.

    The ``vw_volume_anomalies_cn`` view name is intentionally hardcoded (out of
    scope for ADR-0010 — see anomaly_service history).
    """

    def __init__(self, view: IMarketViewRepository):
        self._view = view

    def anomalies(self, min_ratio: float = 3.0, top: int = 20) -> List[dict]:
        df = self._view.execute("""
            SELECT ticker, date, volume, ROUND(avg_vol_20d, 0) AS avg_vol,
                   ROUND(vol_ratio, 2) AS vol_ratio,
                   ROUND(intraday_return, 2) AS ret_pct
            FROM vw_volume_anomalies_cn
            WHERE vol_ratio >= ?
            ORDER BY vol_ratio DESC
            LIMIT ?
        """, [min_ratio, top])
        return df.to_dict(orient="records")

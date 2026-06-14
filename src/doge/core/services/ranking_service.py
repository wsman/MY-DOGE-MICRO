"""RSRS ranking service."""

from typing import List

from doge.core.ports.market_view import IMarketViewRepository


class RankingService:
    """RSRS momentum ranking queries.

    Depends on the :class:`~doge.core.ports.market_view.IMarketViewRepository`
    port (per ADR-0010); this service imports no infrastructure.
    """

    def __init__(self, view: IMarketViewRepository):
        self._view = view

    def rsrs(self, market: str = "cn", top: int = 20) -> List[dict]:
        view = f"vw_rsrs_ranking_{market}"
        df = self._view.execute(f"SELECT * FROM {view} LIMIT ?", [top])
        return df.to_dict(orient="records")

"""Market breadth service."""

from typing import List

from doge.core.ports.market_view import IMarketViewRepository


class BreadthService:
    """Market breadth queries.

    Depends on the :class:`~doge.core.ports.market_view.IMarketViewRepository`
    port (per ADR-0010); this service imports no infrastructure.
    """

    def __init__(self, view: IMarketViewRepository):
        self._view = view

    def breadth(self, market: str = "cn", days: int = 10) -> List[dict]:
        view = f"vw_market_breadth_{market}"
        df = self._view.execute(f"SELECT * FROM {view} LIMIT ?", [days])
        return df.to_dict(orient="records")

"""Scan market use case — orchestrates data-source fetch + persistence + view refresh.

This is a Sprint 007-001 stub. The full orchestration logic is implemented in
S007-005 once the DuckDB/SQLite repository boundary is stable.
"""

from doge.application.contracts.request import ScanMarketRequest
from doge.application.contracts.response import ScanMarketResponse


class ScanMarketUseCase:
    """Orchestrate a full-market data refresh."""

    def __init__(
        self,
        stock_repo,
        data_source,
        refresh_views_callable,
    ) -> None:
        """Initialize with injected ports.

        Args:
            stock_repo: An :class:`~doge.core.ports.repository.IStockRepository`.
            data_source: An :class:`~doge.core.ports.data_source.IMarketDataSource`.
            refresh_views_callable: A callable that materializes DuckDB views.
        """
        self._stock_repo = stock_repo
        self._data_source = data_source
        self._refresh_views = refresh_views_callable

    def execute(self, request: ScanMarketRequest) -> ScanMarketResponse:
        """Run the scan workflow (stub — full logic in S007-005)."""
        return ScanMarketResponse(market=request.market)

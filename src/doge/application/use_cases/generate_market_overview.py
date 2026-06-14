"""Generate market overview report use case.

This is a Sprint 007-001 stub. The full orchestration logic is implemented in
S007-004 once the ai_analysis.market_overview helpers are migrated.
"""

from doge.application.contracts.request import GenerateMarketOverviewRequest
from doge.application.contracts.response import MarketOverviewResponse


class GenerateMarketOverviewUseCase:
    """Generate a Markdown market overview report."""

    def __init__(
        self,
        breadth_service,
        ranking_service,
        anomaly_service,
    ) -> None:
        """Initialize with injected services.

        Args:
            breadth_service: A :class:`~doge.core.services.breadth_service.BreadthService`.
            ranking_service: A :class:`~doge.core.services.ranking_service.RankingService`.
            anomaly_service: A :class:`~doge.core.services.anomaly_service.AnomalyService`.
        """
        self._breadth_service = breadth_service
        self._ranking_service = ranking_service
        self._anomaly_service = anomaly_service

    def execute(self, request: GenerateMarketOverviewRequest) -> MarketOverviewResponse:
        """Run the overview workflow (stub — full logic in S007-004)."""
        return MarketOverviewResponse(market=request.market)

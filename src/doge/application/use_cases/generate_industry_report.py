"""Generate industry report use case.

This is a Sprint 007-001 stub. The full orchestration logic is implemented in
S007-006 once the micro.industry_analyzer helpers are migrated.
"""

from doge.application.contracts.request import GenerateIndustryReportRequest
from doge.application.contracts.response import IndustryReportResponse


class GenerateIndustryReportUseCase:
    """Generate an industry analysis report via an LLM client."""

    def __init__(
        self,
        ranking_service,
        llm_client,
    ) -> None:
        """Initialize with injected service and port.

        Args:
            ranking_service: A :class:`~doge.core.services.ranking_service.RankingService`.
            llm_client: An :class:`~doge.core.ports.llm.ILLMClient`.
        """
        self._ranking_service = ranking_service
        self._llm_client = llm_client

    def execute(self, request: GenerateIndustryReportRequest) -> IndustryReportResponse:
        """Run the industry report workflow (stub — full logic in S007-006)."""
        return IndustryReportResponse(market=request.market)

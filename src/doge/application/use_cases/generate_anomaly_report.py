"""Generate anomaly report use case.

This is a Sprint 007-001 stub. The full orchestration logic is implemented in
S007-004 once the ai_analysis.anomaly_detection helpers are migrated.
"""

from doge.application.contracts.request import GenerateAnomalyReportRequest
from doge.application.contracts.response import AnomalyReportResponse


class GenerateAnomalyReportUseCase:
    """Generate a Markdown anomaly report."""

    def __init__(self, anomaly_service) -> None:
        """Initialize with injected service.

        Args:
            anomaly_service: A :class:`~doge.core.services.anomaly_service.AnomalyService`.
        """
        self._anomaly_service = anomaly_service

    def execute(self, request: GenerateAnomalyReportRequest) -> AnomalyReportResponse:
        """Run the anomaly report workflow (stub — full logic in S007-004)."""
        return AnomalyReportResponse(market=request.market)

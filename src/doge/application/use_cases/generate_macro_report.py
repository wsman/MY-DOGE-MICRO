"""Generate macro report use case — orchestrates market context + LLM call + persistence.

This is a Sprint 007-001 stub. The full orchestration logic is implemented in
S007-006 once the ILLMClient port and DeepSeekClient adapter are wired.
"""

from doge.application.contracts.request import GenerateMacroReportRequest
from doge.application.contracts.response import MacroReportResponse


class GenerateMacroReportUseCase:
    """Generate a macro strategy report via an LLM client."""

    def __init__(
        self,
        view_repo,
        llm_client,
        report_repo,
    ) -> None:
        """Initialize with injected ports.

        Args:
            view_repo: An :class:`~doge.core.ports.market_view.IMarketViewRepository`.
            llm_client: An :class:`~doge.core.ports.llm.ILLMClient`.
            report_repo: An :class:`~doge.core.ports.repository.IReportRepository`.
        """
        self._view_repo = view_repo
        self._llm_client = llm_client
        self._report_repo = report_repo

    def execute(self, request: GenerateMacroReportRequest) -> MacroReportResponse:
        """Run the macro report workflow (stub — full logic in S007-006)."""
        return MacroReportResponse(analyst=request.analyst_model)

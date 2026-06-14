"""Populate stock names use case.

This is a Sprint 007-001 stub. The full orchestration logic is implemented in
S007-004 once the ai_analysis.fetch_name helpers are migrated.
"""

from doge.application.contracts.request import PopulateStockNamesRequest
from doge.application.contracts.response import PopulateStockNamesResponse


class PopulateStockNamesUseCase:
    """Batch-fetch stock names from a metadata source and persist them."""

    def __init__(
        self,
        metadata_source,
        note_repo,
    ) -> None:
        """Initialize with injected ports.

        Args:
            metadata_source: An :class:`~doge.core.ports.metadata.ITickerMetadataSource`.
            note_repo: An :class:`~doge.core.ports.repository.INoteRepository`.
        """
        self._metadata_source = metadata_source
        self._note_repo = note_repo

    def execute(self, request: PopulateStockNamesRequest) -> PopulateStockNamesResponse:
        """Run the populate workflow (stub — full logic in S007-004)."""
        return PopulateStockNamesResponse(market=request.market)

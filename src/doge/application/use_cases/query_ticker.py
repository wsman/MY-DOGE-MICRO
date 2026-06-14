"""Query ticker use case — composite ticker metadata + prices + notes.

This is a Sprint 007-001 stub. The full orchestration logic is implemented in
S007-004 once the metadata and note repository boundaries are stable.
"""

from doge.application.contracts.request import QueryTickerRequest
from doge.application.contracts.response import QueryTickerResponse


class QueryTickerUseCase:
    """Return a composite view of a single ticker."""

    def __init__(
        self,
        stock_repo,
        note_repo,
        metadata_source,
    ) -> None:
        """Initialize with injected ports.

        Args:
            stock_repo: An :class:`~doge.core.ports.repository.IStockRepository`.
            note_repo: An :class:`~doge.core.ports.repository.INoteRepository`.
            metadata_source: An :class:`~doge.core.ports.metadata.ITickerMetadataSource`.
        """
        self._stock_repo = stock_repo
        self._note_repo = note_repo
        self._metadata_source = metadata_source

    def execute(self, request: QueryTickerRequest) -> QueryTickerResponse:
        """Run the query workflow (stub — full logic in S007-004)."""
        return QueryTickerResponse(ticker=request.ticker, market=request.market)

"""Manage notes use case — note CRUD + archive + search orchestration.

Implements the note workflow previously scattered across
``src/ai_analysis/stock_notes.py``. All storage access flows through the
injected :class:`~doge.core.ports.repository.INoteRepository` port.
"""

from typing import Optional

from doge.application.contracts.request import ManageNoteRequest
from doge.application.contracts.response import ManageNoteResponse
from doge.core.ports.repository import INoteRepository


class ManageNotesUseCase:
    """Orchestrate note lifecycle operations."""

    def __init__(self, note_repo: INoteRepository) -> None:
        """Initialize with injected port.

        Args:
            note_repo: An :class:`~doge.core.ports.repository.INoteRepository`.
        """
        self._note_repo = note_repo

    def execute(self, request: ManageNoteRequest) -> ManageNoteResponse:
        """Run the requested note operation."""
        op = request.operation
        if op == "add":
            note_id = self._note_repo.add_note(
                ticker=request.ticker or "",
                note_text=request.note_text or "",
                market=request.market,
                note_type=request.note_type,
                title=request.title,
                tags=request.tags,
                price_at_note=request.price_at_note,
                source=request.source or "user",
                sentiment=request.sentiment,
            )
            return ManageNoteResponse(
                operation="add", success=True, note_id=note_id, count=1
            )

        if op == "delete":
            deleted = self._note_repo.delete_note(request.note_id or -1)
            return ManageNoteResponse(operation="delete", success=deleted)

        if op == "get_notes":
            notes = self._note_repo.get_notes(
                ticker=request.ticker,
                limit=request.limit,
                days_back=request.days,
                note_type=request.note_type,
            )
            return ManageNoteResponse(
                operation="get_notes", notes=notes, count=len(notes)
            )

        if op == "search":
            notes = self._note_repo.search_notes(
                keyword=request.keyword or "", limit=request.limit
            )
            return ManageNoteResponse(
                operation="search", notes=notes, count=len(notes)
            )

        if op == "recent":
            notes = self._note_repo.get_recent_notes(
                days=request.days, limit=request.limit
            )
            return ManageNoteResponse(
                operation="recent", notes=notes, count=len(notes)
            )

        if op == "tracked":
            tickers = self._note_repo.list_tracked_tickers()
            return ManageNoteResponse(
                operation="tracked", notes=tickers, count=len(tickers)
            )

        if op == "get_context":
            ctx = self._note_repo.get_ticker_with_context(
                ticker=request.ticker or "", market=request.market
            )
            return ManageNoteResponse(
                operation="get_context",
                context=ctx,
                count=ctx.get("note_count_total", 0),
            )

        return ManageNoteResponse(
            operation=op,
            success=False,
            message=f"unknown operation: {op}",
        )

    def add_note(
        self,
        ticker: str,
        note_text: str,
        *,
        market: str = "cn",
        note_type: str = "comment",
        title: Optional[str] = None,
        tags: Optional[str] = None,
        price_at_note: Optional[float] = None,
        source: Optional[str] = None,
        sentiment: Optional[str] = None,
    ) -> int:
        """Convenience wrapper for adding a single note."""
        return self._note_repo.add_note(
            ticker=ticker,
            note_text=note_text,
            market=market,
            note_type=note_type,
            title=title,
            tags=tags,
            price_at_note=price_at_note,
            source=source,
            sentiment=sentiment,
        )

    def delete_note(self, note_id: int) -> bool:
        """Convenience wrapper for soft-deleting a note."""
        return self._note_repo.delete_note(note_id)

    def get_notes(
        self,
        ticker: Optional[str] = None,
        *,
        limit: Optional[int] = None,
        days_back: Optional[int] = None,
        note_type: Optional[str] = None,
    ) -> list:
        """Convenience wrapper for listing notes."""
        return self._note_repo.get_notes(
            ticker=ticker,
            limit=limit,
            days_back=days_back,
            note_type=note_type,
        )

    def search_notes(self, keyword: str, limit: int = 50) -> list:
        """Convenience wrapper for searching notes."""
        return self._note_repo.search_notes(keyword, limit=limit)

    def get_recent_notes(self, days: int = 7, limit: int = 100) -> list:
        """Convenience wrapper for recent notes."""
        return self._note_repo.get_recent_notes(days=days, limit=limit)

    def list_tracked_tickers(self) -> list:
        """Convenience wrapper for tracked tickers."""
        return self._note_repo.list_tracked_tickers()

    def get_ticker_with_context(self, ticker: str, market: str = "cn") -> dict:
        """Convenience wrapper for ticker context."""
        return self._note_repo.get_ticker_with_context(ticker, market=market)

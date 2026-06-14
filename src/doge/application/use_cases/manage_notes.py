"""Manage notes use case — note CRUD + archive + search orchestration.

This is a Sprint 007-001 stub. The full orchestration logic is implemented in
S007-004 once the note repository boundary is fully migrated from
src/ai_analysis/stock_notes.py.
"""

from doge.application.contracts.request import ManageNoteRequest
from doge.application.contracts.response import ManageNoteResponse


class ManageNotesUseCase:
    """Orchestrate note lifecycle operations."""

    def __init__(self, note_repo) -> None:
        """Initialize with injected port.

        Args:
            note_repo: An :class:`~doge.core.ports.repository.INoteRepository`.
        """
        self._note_repo = note_repo

    def execute(self, request: ManageNoteRequest) -> ManageNoteResponse:
        """Run the requested note operation (stub — full logic in S007-004)."""
        return ManageNoteResponse(operation=request.operation)

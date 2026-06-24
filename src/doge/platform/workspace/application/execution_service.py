"""Case execution service export."""

from doge.platform.workspace.application.case_service import ResearchCaseService


class CaseExecutionService(ResearchCaseService):
    """Focused entry point for case execution behavior."""


__all__ = ["CaseExecutionService"]

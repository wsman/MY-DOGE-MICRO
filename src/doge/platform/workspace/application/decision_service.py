"""Case decision service export."""

from doge.platform.workspace.application.case_service import ResearchCaseService


class CaseDecisionService(ResearchCaseService):
    """Focused entry point for case decision behavior."""


__all__ = ["CaseDecisionService"]

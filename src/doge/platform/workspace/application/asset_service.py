"""Case asset service export."""

from doge.platform.workspace.application.case_service import ResearchCaseService


class CaseAssetService(ResearchCaseService):
    """Focused entry point for case asset behavior."""


__all__ = ["CaseAssetService"]

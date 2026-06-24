"""Workspace bootstrap container."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from doge.application import composition


@dataclass(frozen=True)
class WorkspaceContainer:
    """Typed entry point for workspace and portfolio wiring."""

    db_path: Path | str | None = None

    def build_portfolio_repository(self):
        return composition.build_portfolio_repository(self.db_path)

    def build_platform_repository(self):
        return composition.build_platform_repository(self.db_path)

    def build_enterprise_governance_repository(self):
        return composition.build_enterprise_governance_repository(self.db_path)

    def build_research_case_service(self):
        return composition.build_research_case_service(db_path=self.db_path)

    def build_workflow_service(self):
        return composition.build_workflow_service(db_path=self.db_path)


def build_workspace_container(db_path: Path | str | None = None) -> WorkspaceContainer:
    """Build the workspace container."""

    return WorkspaceContainer(db_path=db_path)

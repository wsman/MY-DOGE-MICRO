"""Workspace bootstrap container."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from doge.infrastructure.database.enterprise_governance import SQLiteEnterpriseGovernanceRepository
from doge.infrastructure.database.platform_repository import SQLitePlatformRepository
from doge.infrastructure.database.portfolio_repository import SQLitePortfolioRepository, demo_portfolio
from doge.platform.workspace import composition
from doge.platform.workspace.application import ResearchCaseService, WorkflowService


@dataclass(frozen=True)
class WorkspaceContainer:
    """Typed entry point for workspace and portfolio wiring."""

    db_path: Path | str | None = None
    graph_provider: Callable[[], Any] | None = field(default=None, repr=False, compare=False)

    def build_portfolio_repository(self):
        repo = SQLitePortfolioRepository(self.db_path)
        if repo.get("portfolio-demo") is None:
            repo.save(demo_portfolio())
        return repo

    def build_platform_repository(self):
        return SQLitePlatformRepository(self.db_path)

    def build_enterprise_governance_repository(self):
        return SQLiteEnterpriseGovernanceRepository(self.db_path)

    def build_research_case_service(
        self,
        *,
        runtime=None,
        repo=None,
        governance=None,
        capability_registry_enabled: bool = True,
    ) -> ResearchCaseService:
        runtime_container = self.runtime_container()
        return composition.build_research_case_service(
            repo or self.build_platform_repository(),
            governance or self.build_enterprise_governance_repository(),
            runtime or runtime_container.build_persisted_research_agent_runtime(),
            document_repository=runtime_container.build_agent_document_repository(),
            portfolio_repository=self.build_portfolio_repository(),
            capability_registry=runtime_container.build_capability_registry_use_case(),
            capability_registry_enabled=capability_registry_enabled,
        )

    def build_workflow_service(self, *, repo=None, governance=None) -> WorkflowService:
        return composition.build_workflow_service(
            repo or self.build_platform_repository(),
            governance or self.build_enterprise_governance_repository(),
        )

    def runtime_container(self):
        """Return the graph-owned runtime container."""

        return self._process_graph().runtime_container

    def _process_graph(self):
        if self.graph_provider is not None:
            return self.graph_provider()
        from doge.bootstrap.processes import build_embedded_process

        return build_embedded_process(db_path=self.db_path)


def build_workspace_container(db_path: Path | str | None = None) -> WorkspaceContainer:
    """Build the workspace container."""

    from doge.bootstrap.processes import build_embedded_process

    return build_embedded_process(db_path=db_path).workspace_container

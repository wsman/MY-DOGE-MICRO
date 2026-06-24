"""Bounded-context composition root for Workspace & Workflow (bc-05).

Constructs the workspace / project / research-case / workflow application
services from their repository and runtime dependencies. This is the
composition root for the bc-05 bounded context.

Constraints (enforced by P2B acceptance):

- This module does NOT import ``doge.application.composition``.
- Builders accept already-wired dependencies (repositories, runtime); they do
  not construct infrastructure adapters. The governance repository is always a
  required argument, so enterprise governance and tenant fail-closed behavior
  stay intact regardless of where the dependencies were assembled.
"""

from __future__ import annotations

from typing import Any

from doge.platform.workspace.application import (
    ProjectService,
    ResearchCaseService,
    WorkflowService,
    WorkspaceService,
)


def build_workspace_service(repo: Any, governance: Any) -> WorkspaceService:
    """Build the workspace service bound to a platform repo + governance."""
    return WorkspaceService(repo, governance)


def build_project_service(repo: Any, governance: Any) -> ProjectService:
    """Build the project service bound to a platform repo + governance."""
    return ProjectService(repo, governance)


def build_research_case_service(
    repo: Any,
    governance: Any,
    runtime: Any,
    *,
    document_repository: Any | None = None,
    portfolio_repository: Any | None = None,
    capability_registry: Any | None = None,
    capability_registry_enabled: bool = False,
) -> ResearchCaseService:
    """Build the research-case service with optional execution collaborators.

    ``capability_registry_enabled`` defaults to ``False`` so a bare call does
    not enable a (possibly ``None``) capability registry; callers that supply a
    registry pass ``capability_registry_enabled=True`` explicitly.
    """
    return ResearchCaseService(
        repo,
        governance,
        runtime,
        document_repository=document_repository,
        portfolio_repository=portfolio_repository,
        capability_registry=capability_registry,
        capability_registry_enabled=capability_registry_enabled,
    )


def build_workflow_service(repo: Any, governance: Any) -> WorkflowService:
    """Build the workflow-template service bound to a platform repo + governance."""
    return WorkflowService(repo, governance)

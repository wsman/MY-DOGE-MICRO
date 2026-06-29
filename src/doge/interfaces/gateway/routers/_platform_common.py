"""Shared helpers for the focused v1 platform sub-routers.

Holds the feature guards, FastAPI service-factory dependencies, the request
context builder, and the platform-error translator used across the
capabilities / workspaces / projects / cases / workflows routers. The
sub-routers import from here so ``platform.py`` can shrink to a compatibility
aggregator.
"""

from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, Request

from doge.application.use_cases.capability_registry import BuildCapabilityRegistry
from doge.application.use_cases.run_summary import BuildRunSummary
from doge.core.ports.agent_runtime import IResearchAgentRuntime
from doge.core.ports.document_repository import IDocumentRepository
from doge.core.ports.enterprise_governance import IEnterpriseGovernanceRepository
from doge.core.ports.portfolio_repository import IPortfolioRepository
from doge.core.ports.platform_repository import IPlatformRepository
from doge.interfaces.api import deps
from doge.interfaces.api.enterprise_access import (
    enterprise_context,
    is_enterprise_request,
    request_id,
)
from doge.platform.workspace import composition
from doge.platform.workspace import (
    PlatformAccessDeniedError,
    PlatformFeatureDisabledError,
    PlatformNotFoundError,
    PlatformRequestContext,
    PlatformServiceError,
    PlatformValidationError,
    ProjectService,
    ResearchCaseService,
    WorkflowService,
    WorkspaceService,
)


# ── Feature guards ──


def require_platform_objects(settings=Depends(deps.get_settings_dep)) -> None:
    if not settings.features.platform_objects:
        raise HTTPException(404, "platform objects API disabled")


def require_workflow_templates(settings=Depends(deps.get_settings_dep)) -> None:
    if not settings.features.workflow_templates:
        raise HTTPException(404, "workflow templates API disabled")


def require_capability_registry(settings=Depends(deps.get_settings_dep)) -> None:
    if not settings.features.capability_registry:
        raise HTTPException(404, "capability registry API disabled")


# ── Service factories ──


def build_workspace_service(
    repo: IPlatformRepository = Depends(deps.get_platform_repository),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
) -> WorkspaceService:
    return composition.build_workspace_service(repo, governance)


def build_project_service(
    repo: IPlatformRepository = Depends(deps.get_platform_repository),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
) -> ProjectService:
    return composition.build_project_service(repo, governance)


def build_research_case_service(
    repo: IPlatformRepository = Depends(deps.get_platform_repository),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
) -> ResearchCaseService:
    return composition.build_research_case_service(repo, governance, runtime)


def build_research_case_execution_service(
    repo: IPlatformRepository = Depends(deps.get_platform_repository),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
    documents: IDocumentRepository = Depends(deps.get_agent_document_repository),
    portfolios: IPortfolioRepository = Depends(deps.get_portfolio_repository),
    capability_registry: BuildCapabilityRegistry = Depends(deps.get_capability_registry_use_case),
    settings=Depends(deps.get_settings_dep),
) -> ResearchCaseService:
    return composition.build_research_case_service(
        repo,
        governance,
        runtime,
        document_repository=documents,
        portfolio_repository=portfolios,
        capability_registry=capability_registry,
        capability_registry_enabled=settings.features.capability_registry,
    )


def build_workflow_service(
    repo: IPlatformRepository = Depends(deps.get_platform_repository),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
) -> WorkflowService:
    return composition.build_workflow_service(repo, governance)


# ── Request context + error translation ──


def platform_context(request: Request) -> PlatformRequestContext:
    return PlatformRequestContext(
        enterprise_context=enterprise_context(request),
        enterprise_request=is_enterprise_request(request),
        request_id=request_id(request),
    )


def raise_platform_error(exc: PlatformServiceError) -> None:
    if isinstance(exc, PlatformAccessDeniedError):
        raise HTTPException(403, str(exc))
    if isinstance(exc, PlatformValidationError):
        if getattr(exc, "details", None):
            raise HTTPException(400, {"message": str(exc), "details": exc.details})
        raise HTTPException(400, str(exc))
    if isinstance(exc, (PlatformFeatureDisabledError, PlatformNotFoundError)):
        raise HTTPException(404, str(exc))
    raise HTTPException(500, "platform service error")


# Re-exported for type-checking consumers; BuildRunSummary is used by the cases router.
__all__ = [
    "Any",
    "BuildRunSummary",
    "PlatformRequestContext",
    "PlatformServiceError",
    "build_project_service",
    "build_research_case_execution_service",
    "build_research_case_service",
    "build_workflow_service",
    "build_workspace_service",
    "platform_context",
    "raise_platform_error",
    "require_capability_registry",
    "require_platform_objects",
    "require_workflow_templates",
]

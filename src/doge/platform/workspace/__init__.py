"""Workspace & Workflow facade."""

from doge.application.use_cases.capability_registry import BuildCapabilityRegistry
from doge.core.domain.platform_models import (
    CaseRunLink,
    Project,
    ResearchCase,
    WorkflowTemplate,
    WorkflowTemplateRunLink,
    Workspace,
    to_dict,
)
from doge.core.domain.workflow_template import TemplateRunInput, build_template_run_request
from doge.core.ports.capability_provider import ICapabilityProvider
from doge.core.ports.platform_repository import IPlatformRepository
from doge.platform.workspace.service import (
    CaseRunCreate,
    CaseRunCreateResult,
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

__all__ = [
    "BuildCapabilityRegistry",
    "CaseRunCreate",
    "CaseRunCreateResult",
    "CaseRunLink",
    "ICapabilityProvider",
    "IPlatformRepository",
    "PlatformAccessDeniedError",
    "PlatformFeatureDisabledError",
    "PlatformNotFoundError",
    "PlatformRequestContext",
    "PlatformServiceError",
    "PlatformValidationError",
    "Project",
    "ProjectService",
    "ResearchCase",
    "ResearchCaseService",
    "TemplateRunInput",
    "WorkflowTemplate",
    "WorkflowTemplateRunLink",
    "WorkflowService",
    "Workspace",
    "WorkspaceService",
    "build_template_run_request",
    "to_dict",
]

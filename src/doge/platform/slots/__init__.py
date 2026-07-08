"""Slot Platform Foundation (ADR-0042).

Public contract for modular platform contributions. A *slot* declares what it
provides (tools, capabilities, ...), what it requires, its permissions, health,
feature flags, and compatibility. The :class:`SlotRegistry` aggregates slot
contributions for runtime assembly.

Sprint 033 ships only the ``tool`` slot type (``market.core``); the contract
declares the full :class:`SlotType` enum so future sprints migrate model,
workflow, data, document, ui, gateway, governance, eval, and watcher slots
without changing the manifest schema.

This package is deliberately pure: it imports only ``doge.core.*``,
``doge.shared.*`` and the standard library. It must not import ``doge.config``,
``doge.infrastructure``, ``doge.adapters``, ``doge.products``,
``doge.application.tools``, ``doge.bootstrap`` or ``doge.interfaces``;
``tests/unit/architecture/test_slot_boundary.py`` ratchets this.
"""

from __future__ import annotations

from doge.platform.slots.contracts import (
    ISlot,
    SLOT_SERVICE_AGENT_BACKEND_REGISTRY,
    SLOT_SERVICE_DATA_SOURCE_REGISTRY,
    SLOT_SERVICE_DOCUMENT_PARSER_REGISTRY,
    SLOT_SERVICE_EVENT_BUS,
    SLOT_SERVICE_FASTAPI_APP,
    SLOT_SERVICE_GOVERNANCE_REPOSITORY,
    SLOT_SERVICE_PLATFORM_REPOSITORY,
    SLOT_SERVICE_SECRET_PROVIDER,
    SlotContribution,
    SlotContext,
    SlotStatus,
    ToolServiceProtocol,
)
from doge.platform.slots.activation import (
    SlotBundleActivation,
    SlotBundleActivationState,
    policy_for_activation,
)
from doge.platform.slots.bundles import SlotBundle, SlotBundleStatus
from doge.platform.slots.errors import (
    SlotAlreadyRegisteredError,
    SlotConfigurationError,
    SlotError,
    SlotManifestValidationError,
    UnknownSlotError,
)
from doge.platform.slots.enforcement import (
    SlotEnforcementDecision,
    SlotEnforcementPolicy,
)
from doge.platform.slots.facets import (
    DataSourceContribution,
    DocumentParserContribution,
    EvalSuiteContribution,
    GatewayRouteContribution,
    GovernancePolicyContribution,
    ModelBackendContribution,
    UIPanelContribution,
    WatcherContribution,
    WatcherDecision,
    WorkflowTemplateContribution,
)
from doge.platform.slots.manifest import (
    SCHEMA_VERSION,
    SlotCompatibility,
    SlotHealth,
    SlotManifest,
    SlotPermissions,
    SlotProvides,
    SlotRequirement,
    SlotType,
    load_slot_manifest,
)
from doge.platform.slots.kernel import SlotKernel
from doge.platform.slots.lifecycle import (
    SlotLifecycle,
    SlotLifecycleRecord,
    SlotLifecycleState,
)
from doge.platform.slots.loader import ManifestOnlySlot, SlotLoader
from doge.platform.slots.install import (
    canonical_manifest_bytes,
    sign_slot_manifest,
    SlotInstaller,
    SlotInstallPolicy,
    SlotInstallResult,
    SlotSignatureVerification,
    verify_slot_signature,
)
from doge.platform.slots.policy import SlotPolicy
from doge.platform.slots.registry import SlotRegistry, SlotStatusRecord

__all__ = [
    "ISlot",
    "SCHEMA_VERSION",
    "SLOT_SERVICE_AGENT_BACKEND_REGISTRY",
    "SLOT_SERVICE_DATA_SOURCE_REGISTRY",
    "SLOT_SERVICE_DOCUMENT_PARSER_REGISTRY",
    "SLOT_SERVICE_EVENT_BUS",
    "SLOT_SERVICE_FASTAPI_APP",
    "SLOT_SERVICE_GOVERNANCE_REPOSITORY",
    "SLOT_SERVICE_PLATFORM_REPOSITORY",
    "SLOT_SERVICE_SECRET_PROVIDER",
    "DataSourceContribution",
    "DocumentParserContribution",
    "EvalSuiteContribution",
    "GatewayRouteContribution",
    "GovernancePolicyContribution",
    "ModelBackendContribution",
    "ManifestOnlySlot",
    "SlotAlreadyRegisteredError",
    "SlotBundle",
    "SlotBundleActivation",
    "SlotBundleActivationState",
    "SlotBundleStatus",
    "SlotCompatibility",
    "SlotConfigurationError",
    "SlotContribution",
    "SlotContext",
    "SlotError",
    "SlotEnforcementDecision",
    "SlotEnforcementPolicy",
    "SlotHealth",
    "SlotInstaller",
    "SlotInstallPolicy",
    "SlotInstallResult",
    "SlotKernel",
    "SlotLifecycle",
    "SlotLifecycleRecord",
    "SlotLifecycleState",
    "SlotLoader",
    "SlotManifest",
    "SlotManifestValidationError",
    "SlotPermissions",
    "SlotProvides",
    "SlotPolicy",
    "SlotRegistry",
    "SlotRequirement",
    "SlotStatus",
    "SlotStatusRecord",
    "SlotType",
    "SlotSignatureVerification",
    "ToolServiceProtocol",
    "UIPanelContribution",
    "UnknownSlotError",
    "WatcherContribution",
    "WatcherDecision",
    "WorkflowTemplateContribution",
    "load_slot_manifest",
    "policy_for_activation",
    "verify_slot_signature",
    "canonical_manifest_bytes",
]
    "sign_slot_manifest",

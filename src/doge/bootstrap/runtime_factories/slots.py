"""Slot-aware runtime factory wiring (ADR-0042/0043).

When ``DOGE_FEATURE_SLOT_PLATFORM`` is on, the default tool registry is assembled
from slot contributions plus the remaining (non-slot-owned) descriptors,
re-using the existing :meth:`ToolRegistry.include_descriptors` seam against the
same :class:`ToolApplicationService` instance. The result is byte-equivalent to
the legacy factory path because the contribution's ``executor`` IS the service
and its ``tools`` ARE the service's own descriptors filtered by name.

This module is the only layer permitted to import across products / platform /
application when wiring slots; construction lives in ``bootstrap/`` while the
contract lives in :mod:`doge.platform.slots` (see
``tests/unit/architecture/test_bootstrap_owns_factories.py``).
"""

from __future__ import annotations

from dataclasses import fields, replace
from inspect import signature
from pathlib import Path
from typing import Any

from doge.application.tools.registry import ToolRegistry
from doge.bootstrap.runtime_factories.builtin_model_slot import ModelKimiAgentSdkSlot
from doge.config import get_settings
from doge.config.settings import parse_slot_trusted_publisher_keys
from doge.core.ports.slot_runtime_executor import DisabledSlotRuntimeExecutor
from doge.core.ports.enterprise_governance import EnterpriseAuditEvent
from doge.eval.slot import LocalEvalCasesSlot
from doge.eval.suites import EvalSuiteRegistry
from doge.infrastructure.data_source.slot import TDXDataSourceSlot, YFinanceDataSourceSlot
from doge.infrastructure.documents.slot import LocalDocumentParserSlot
from doge.interfaces.gateway.slot import SlotDiscoveryGatewaySlot
from doge.products.market.data_sources import DataSourceRegistry
from doge.platform.governance.slot import (
    CompositeToolEntitlementChecker,
    ToolGovernancePolicySlot,
)
from doge.platform.governance.actions_slot import GovernanceActionsSlot
from doge.platform.governance.compliance_slot import ComplianceScreeningSlot
from doge.platform.evidence.document_parsers import ParserDispatcher
from doge.platform.runtime.slot import RuntimeEventWatcherSlot
from doge.platform.runtime.watchers import RuntimeEventWatcherMiddleware
from doge.platform.slots import (
    SLOT_SERVICE_SECRET_PROVIDER,
    SlotBundle,
    SlotBundleActivationState,
    SlotAccessEvent,
    SlotConfigurationError,
    SlotContribution,
    SlotContext,
    SlotEnforcementPolicy,
    SlotInstallPolicy,
    SlotInstaller,
    SlotKernel,
    SlotLoader,
    SlotPolicy,
    SlotRegistry,
    SlotType,
    UnknownSlotError,
    SandboxedSlotRuntimeExecutor,
    guard_network_port,
    guard_secret_provider,
    slot_permission_context,
    slot_scoped_executor,
    slot_scoped_object,
    policy_for_activation,
    sign_slot_manifest,
)
from doge.platform.workspace.slot import WorkflowTemplatesSlot
from doge.platform.workspace.ui_panels import UIPanelRegistry
from doge.platform.workspace.ui_slot import ResearchWorkspaceUISlot
from doge.products.market.slot import MarketCoreSlot
from doge.products.portfolio.slot import PortfolioCoreSlot
from doge.products.quant.slot import QuantLabSlot
from doge.products.research.slot import EvidenceCoreSlot


_BUILTIN_SLOT_BUNDLES = (
    SlotBundle(
        id="bundle.local_analyst",
        name="Local Analyst",
        description="Local research bundle for market, document, workflow, eval, and model slots.",
        slot_ids=(
            "market.core",
            "portfolio.core",
            "evidence.core",
            "quant.lab",
            "governance.actions",
            "compliance.screening",
            "model.kimi_agent_sdk",
            "data.tdx",
            "data.yfinance",
            "document.local_parser",
            "workflow.templates",
            "eval.local_cases",
            "governance.tool_policy",
            "watcher.runtime_events",
        ),
    ),
    SlotBundle(
        id="bundle.daemon_operator",
        name="Daemon Operator",
        description="Operator-facing daemon discovery and runtime watcher bundle.",
        slot_ids=(
            "gateway.slots",
            "watcher.runtime_events",
        ),
    ),
    SlotBundle(
        id="bundle.research_workspace",
        name="Research Workspace",
        description="Research workspace bundle over documents, data, workflows, and eval.",
        slot_ids=(
            "market.core",
            "portfolio.core",
            "evidence.core",
            "quant.lab",
            "data.tdx",
            "data.yfinance",
            "document.local_parser",
            "workflow.templates",
            "eval.local_cases",
            "gateway.slots",
            "ui.research_workspace",
        ),
    ),
    SlotBundle(
        id="bundle.enterprise_safe",
        name="Enterprise Safe",
        description="Enterprise governance/watchers bundle with local demo model disabled.",
        slot_ids=(
            "governance.tool_policy",
            "watcher.runtime_events",
            "gateway.slots",
        ),
        disabled_slot_ids=("model.kimi_agent_sdk",),
    ),
)

_SLOT_BUNDLE_ACTIVATION = SlotBundleActivationState()


def build_builtin_slot_registry(settings: Any | None = None) -> SlotRegistry:
    """Construct the registry of built-in slots."""
    resolved_settings = settings if settings is not None else get_settings()
    registry = SlotRegistry()
    registry.register(MarketCoreSlot())
    registry.register(PortfolioCoreSlot())
    registry.register(EvidenceCoreSlot())
    registry.register(QuantLabSlot())
    registry.register(GovernanceActionsSlot())
    registry.register(ComplianceScreeningSlot())
    registry.register(TDXDataSourceSlot())
    registry.register(YFinanceDataSourceSlot())
    registry.register(ModelKimiAgentSdkSlot())
    registry.register(WorkflowTemplatesSlot())
    registry.register(ToolGovernancePolicySlot())
    registry.register(RuntimeEventWatcherSlot())
    registry.register(LocalDocumentParserSlot())
    registry.register(SlotDiscoveryGatewaySlot())
    registry.register(LocalEvalCasesSlot())
    registry.register(ResearchWorkspaceUISlot())
    _register_manifest_only_slots(registry, resolved_settings)
    return registry


def build_builtin_slot_kernel(
    policy: SlotPolicy | None = None,
    *,
    activation_repo: Any | None = None,
    enforcement: SlotEnforcementPolicy | None = None,
    settings: Any | None = None,
) -> SlotKernel:
    """Construct the built-in slot kernel over the built-in registry and bundles."""

    resolved_settings = settings if settings is not None else get_settings()
    registry = _build_builtin_slot_registry_for_settings(resolved_settings)
    bundles = _bundles_supported_by(registry)
    effective_policy = policy
    if effective_policy is None and resolved_settings.features.slot_loader:
        effective_policy = policy_for_activation(
            _active_bundle_activation(resolved_settings, activation_repo),
            bundles,
        )
    return SlotKernel(
        registry,
        policy=effective_policy,
        enforcement=enforcement,
        bundles=bundles,
    )


def activate_slot_bundle(
    bundle_id: str,
    settings: Any | None = None,
    *,
    activation_repo: Any | None = None,
    governance_repo: Any | None = None,
    actor_hash: str = "local-operator",
    tenant_id: str = "local",
    request_id: str | None = None,
) -> dict[str, Any]:
    """Activate a built-in bundle and persist the active bundle pointer."""

    resolved_settings = settings if settings is not None else get_settings()
    if not resolved_settings.features.slot_platform:
        raise SlotConfigurationError("slot platform is disabled")
    if not resolved_settings.features.slot_loader:
        raise SlotConfigurationError("slot loader and bundle activation are disabled")
    registry = _build_builtin_slot_registry_for_settings(resolved_settings)
    bundle = _find_bundle(bundle_id, _bundles_supported_by(registry))
    repo = _activation_repo_for_settings(resolved_settings, activation_repo)
    record = repo.set_active(bundle.id, actor_hash)
    activation = _SLOT_BUNDLE_ACTIVATION.replace(
        bundle_id=record.bundle_id,
        activated_at=record.activated_at,
        actor_hash=record.actor_hash,
    )
    row = _find_bundle_row(
        bundle.id,
        build_slot_bundle_rows(resolved_settings, activation_repo=repo),
    )
    _append_slot_bundle_audit(
        "activate",
        bundle.id,
        settings=resolved_settings,
        governance_repo=governance_repo,
        actor_hash=actor_hash,
        tenant_id=tenant_id,
        request_id=request_id,
    )
    return {
        "status": "activated",
        "active_bundle_id": activation.bundle_id,
        "bundle": row,
    }


def deactivate_slot_bundle(
    settings: Any | None = None,
    *,
    activation_repo: Any | None = None,
    governance_repo: Any | None = None,
    actor_hash: str = "local-operator",
    tenant_id: str = "local",
    request_id: str | None = None,
) -> dict[str, Any]:
    """Clear the persisted active bundle pointer."""

    resolved_settings = settings if settings is not None else get_settings()
    if not resolved_settings.features.slot_platform:
        raise SlotConfigurationError("slot platform is disabled")
    if not resolved_settings.features.slot_loader:
        raise SlotConfigurationError("slot loader and bundle activation are disabled")
    previous = _active_bundle_activation(resolved_settings, activation_repo)
    repo = _activation_repo_for_settings(resolved_settings, activation_repo)
    repo.clear()
    _SLOT_BUNDLE_ACTIVATION.clear()
    _append_slot_bundle_audit(
        "deactivate",
        previous.bundle_id or "*",
        settings=resolved_settings,
        governance_repo=governance_repo,
        actor_hash=actor_hash,
        tenant_id=tenant_id,
        request_id=request_id,
    )
    return {
        "status": "deactivated",
        "active_bundle_id": None,
    }


def install_slot(
    source: str,
    settings: Any | None = None,
    *,
    secret_provider: Any | None = None,
    signing_repo: Any | None = None,
) -> dict[str, Any]:
    """Install a third-party manifest as a local manifest-only slot preview."""

    resolved_settings = settings if settings is not None else get_settings()
    if not resolved_settings.features.slot_platform:
        raise SlotConfigurationError("slot platform is disabled")
    if not resolved_settings.features.slot_loader:
        raise SlotConfigurationError("slot loader is disabled")
    if not resolved_settings.features.slot_install:
        raise SlotConfigurationError("slot install is disabled")
    result = SlotInstaller().install(
        source,
        install_dir=resolved_settings.slots.install_dir,
        policy=_slot_install_policy(
            resolved_settings,
            secret_provider=secret_provider,
            signing_repo=signing_repo,
        ),
    )
    return result.to_dict()


def sign_slot(
    manifest: str,
    *,
    private_key_path: str,
    key_id: str,
    settings: Any | None = None,
) -> dict[str, Any]:
    """Sign a slot manifest with an Ed25519 private key."""

    resolved_settings = settings if settings is not None else get_settings()
    if not resolved_settings.features.slot_platform:
        raise SlotConfigurationError("slot platform is disabled")
    if not resolved_settings.features.slot_install:
        raise SlotConfigurationError("slot install is disabled")
    return sign_slot_manifest(
        manifest,
        private_key_path=private_key_path,
        key_id=key_id,
    )


def revoke_slot_signing_key(
    key_id: str,
    *,
    reason: str | None = None,
    actor_hash: str = "local-cli",
    settings: Any | None = None,
    signing_repo: Any | None = None,
) -> dict[str, Any]:
    """Revoke a trusted slot publisher key for future install verification."""

    resolved_settings = settings if settings is not None else get_settings()
    if not resolved_settings.features.slot_platform:
        raise SlotConfigurationError("slot platform is disabled")
    if not resolved_settings.features.slot_install:
        raise SlotConfigurationError("slot install is disabled")
    record = _slot_signing_repo_for_settings(resolved_settings, signing_repo).revoke(
        key_id,
        reason=reason,
        actor_hash=actor_hash,
    )
    return {
        "status": "revoked",
        "key_id": record.key_id,
        "revoked_at": record.revoked_at,
        "reason": record.reason,
        "actor_hash": record.actor_hash,
    }


def clear_slot_bundle_activation(
    settings: Any | None = None,
    *,
    activation_repo: Any | None = None,
) -> None:
    """Clear bundle activation. Intended for tests and diagnostics."""

    _SLOT_BUNDLE_ACTIVATION.clear()
    resolved_settings = settings if settings is not None else get_settings()
    _activation_repo_for_settings(resolved_settings, activation_repo).clear()


def build_slot_runtime_executor(settings: Any | None = None) -> Any:
    """Build the configured slot runtime executor boundary."""

    resolved_settings = settings if settings is not None else get_settings()
    if not _slot_runtime_interception_enabled(resolved_settings):
        return DisabledSlotRuntimeExecutor()
    return SandboxedSlotRuntimeExecutor(
        audit_sink=_slot_runtime_audit_sink(resolved_settings),
    )


def build_slot_aware_tool_registry(
    gateway_container_fn: Any,
    *,
    entitlement_checker: Any = None,
    context: Any = None,
    settings: Any | None = None,
) -> ToolRegistry:
    """Assemble a ``ToolRegistry`` from slot contributions + remaining descriptors.

    Slot-owned descriptors are registered first via the same
    ``include_descriptors`` seam the legacy factory uses (against the same
    service), then the remaining descriptors are registered so nothing is
    double-registered (``ToolRegistry.register`` appends to ``self.schemas``
    without dedup).
    """
    service = gateway_container_fn().build_tool_application_service()
    resolved_settings = settings if settings is not None else get_settings()

    slot_context = SlotContext(
        settings=resolved_settings,
        feature_flags=_feature_flags(resolved_settings),
        tool_application_service=service,
    )

    slot_kernel = build_builtin_slot_kernel(
        enforcement=_slot_enforcement_policy(resolved_settings),
        settings=resolved_settings,
    )
    contributions = slot_kernel.resolve_contributions(slot_context, slot_type=SlotType.TOOL)
    interception_enabled = _slot_runtime_interception_enabled(resolved_settings)
    audit_sink = _slot_runtime_audit_sink(resolved_settings) if interception_enabled else None

    effective_entitlement = build_slot_aware_entitlement_checker(
        entitlement_checker,
        settings=resolved_settings,
    )
    registry = ToolRegistry(entitlement_checker=effective_entitlement, context=context)
    slot_owned: set[str] = set(_slot_manifest_tool_names(slot_kernel))
    for contribution in contributions:
        if not contribution.tools:
            continue
        if contribution.executor is None:
            raise SlotConfigurationError(
                f"slot {contribution.slot_id} contributed tools without an executor"
            )
        manifest = _slot_manifest_for_contribution(slot_kernel, contribution)
        executor = slot_scoped_executor(
            contribution.executor,
            contribution.slot_id,
            manifest.permissions,
            enabled=interception_enabled,
            audit_sink=audit_sink,
        )
        registry.include_descriptors(contribution.tools, executor)

    remaining = tuple(
        descriptor
        for descriptor in service.tool_descriptors()
        if descriptor.name not in slot_owned
    )
    registry.include_descriptors(remaining, service)
    return registry


def build_slot_aware_agent_backends(
    gateway_container_fn: Any,
    secret_provider: Any = None,
    *,
    settings: Any | None = None,
) -> dict[str, Any]:
    """Assemble agent backends from model slot contributions."""

    if secret_provider is None:
        secret_provider = gateway_container_fn().build_secret_provider()
    resolved_settings = settings if settings is not None else get_settings()
    interception_enabled = _slot_runtime_interception_enabled(resolved_settings)
    audit_sink = _slot_runtime_audit_sink(resolved_settings) if interception_enabled else None
    slot_context = SlotContext(
        settings=resolved_settings,
        feature_flags=_feature_flags(resolved_settings),
        service_locator=lambda service_id: (
            secret_provider if service_id == SLOT_SERVICE_SECRET_PROVIDER else None
        ),
    )
    slot_kernel = build_builtin_slot_kernel(
        enforcement=_slot_enforcement_policy(resolved_settings),
        settings=resolved_settings,
    )
    contributions = slot_kernel.resolve_contributions(slot_context, slot_type=SlotType.MODEL)

    backends: dict[str, Any] = {}
    for contribution in contributions:
        manifest = _slot_manifest_for_contribution(slot_kernel, contribution)
        guarded_secret_provider = guard_secret_provider(
            secret_provider,
            enabled=interception_enabled,
            audit_sink=audit_sink,
        )
        contribution_context = SlotContext(
            settings=resolved_settings,
            feature_flags=_feature_flags(resolved_settings),
            service_locator=lambda service_id, provider=guarded_secret_provider: (
                provider if service_id == SLOT_SERVICE_SECRET_PROVIDER else None
            ),
        )
        for backend in contribution.model_backends:
            if backend.backend_id in backends:
                raise SlotConfigurationError(
                    f"duplicate model backend contribution: {backend.backend_id}"
                )
            with slot_permission_context(
                contribution.slot_id,
                manifest.permissions,
                enforce=interception_enabled,
                audit_sink=audit_sink,
            ):
                backend_instance = backend.factory(contribution_context)
            guarded_backend = guard_network_port(
                backend_instance,
                enabled=interception_enabled,
                audit_sink=audit_sink,
                methods=("chat",),
            )
            backends[backend.backend_id] = slot_scoped_object(
                guarded_backend,
                contribution.slot_id,
                manifest.permissions,
                enabled=interception_enabled,
                audit_sink=audit_sink,
            )
    return backends


def build_slot_aware_workflow_templates(
    *,
    settings: Any | None = None,
) -> tuple[dict[str, Any], ...]:
    """Assemble built-in workflow template definitions from workflow slots."""

    resolved_settings = settings if settings is not None else get_settings()
    slot_context = SlotContext(
        settings=resolved_settings,
        feature_flags=_feature_flags(resolved_settings),
    )
    slot_kernel = build_builtin_slot_kernel(
        enforcement=_slot_enforcement_policy(resolved_settings),
        settings=resolved_settings,
    )
    contributions = slot_kernel.resolve_contributions(
        slot_context,
        slot_type=SlotType.WORKFLOW,
    )

    templates: list[dict[str, Any]] = []
    seen: set[str] = set()
    interception_enabled = _slot_runtime_interception_enabled(resolved_settings)
    audit_sink = _slot_runtime_audit_sink(resolved_settings) if interception_enabled else None
    for contribution in contributions:
        manifest = _slot_manifest_for_contribution(slot_kernel, contribution)
        for workflow in contribution.workflows:
            if workflow.slug in seen:
                raise SlotConfigurationError(
                    f"duplicate workflow template contribution: {workflow.slug}"
                )
            with slot_permission_context(
                contribution.slot_id,
                manifest.permissions,
                enforce=interception_enabled,
                audit_sink=audit_sink,
            ):
                template = dict(workflow.template_factory(slot_context))
            if template.get("slug") != workflow.slug:
                raise SlotConfigurationError(
                    f"workflow contribution {workflow.slug} returned mismatched "
                    "template slug "
                    f"{template.get('slug')!r}"
                )
            templates.append(template)
            seen.add(workflow.slug)
    return tuple(templates)


def build_slot_aware_entitlement_checker(
    entitlement_checker: Any = None,
    *,
    settings: Any | None = None,
) -> Any:
    """Compose explicit and governance-slot entitlement checkers.

    When no governance slot is enabled, returns the caller-supplied checker
    unchanged. This keeps the flag-on tool registry path equivalent unless
    ``DOGE_FEATURE_SLOT_GOVERNANCE`` is explicitly enabled.
    """

    resolved_settings = settings if settings is not None else get_settings()
    slot_context = SlotContext(
        settings=resolved_settings,
        feature_flags=_feature_flags(resolved_settings),
    )
    slot_kernel = build_builtin_slot_kernel(enforcement=_slot_enforcement_policy(resolved_settings), settings=resolved_settings)
    contributions = slot_kernel.resolve_contributions(
        slot_context,
        slot_type=SlotType.GOVERNANCE,
    )

    checkers: list[Any] = []
    if entitlement_checker is not None:
        checkers.append(entitlement_checker)

    seen_policy_ids: set[str] = set()
    for contribution in contributions:
        for policy in contribution.governance_policies:
            if policy.policy_id in seen_policy_ids:
                raise SlotConfigurationError(
                    f"duplicate governance policy contribution: {policy.policy_id}"
                )
            seen_policy_ids.add(policy.policy_id)
            if policy.entitlement_checker_factory is None:
                continue
            checker = policy.entitlement_checker_factory(slot_context)
            if checker is None:
                raise SlotConfigurationError(
                    f"governance policy {policy.policy_id} returned no entitlement checker"
                )
            checkers.append(checker)

    if not checkers:
        return entitlement_checker
    if len(checkers) == 1:
        return checkers[0]
    return CompositeToolEntitlementChecker(checkers)


def build_slot_aware_runtime_event_watcher(
    *,
    settings: Any | None = None,
) -> Any:
    """Assemble runtime event watcher middleware from watcher slots."""

    resolved_settings = settings if settings is not None else get_settings()
    slot_context = SlotContext(
        settings=resolved_settings,
        feature_flags=_feature_flags(resolved_settings),
    )
    slot_kernel = build_builtin_slot_kernel(enforcement=_slot_enforcement_policy(resolved_settings), settings=resolved_settings)
    contributions = slot_kernel.resolve_contributions(
        slot_context,
        slot_type=SlotType.WATCHER,
    )

    watchers: list[Any] = []
    seen_watcher_ids: set[str] = set()
    for contribution in contributions:
        for watcher in contribution.watchers:
            if watcher.watcher_id in seen_watcher_ids:
                raise SlotConfigurationError(
                    f"duplicate watcher contribution: {watcher.watcher_id}"
                )
            seen_watcher_ids.add(watcher.watcher_id)
            watchers.append(watcher)

    if not watchers:
        return None
    return RuntimeEventWatcherMiddleware(watchers, slot_context)


def build_slot_aware_document_parser(
    *,
    settings: Any | None = None,
) -> Any:
    """Assemble a document parser dispatcher from document slot contributions."""

    resolved_settings = settings if settings is not None else get_settings()
    slot_context = SlotContext(
        settings=resolved_settings,
        feature_flags=_feature_flags(resolved_settings),
    )
    slot_kernel = build_builtin_slot_kernel(enforcement=_slot_enforcement_policy(resolved_settings), settings=resolved_settings)
    contributions = slot_kernel.resolve_contributions(
        slot_context,
        slot_type=SlotType.DOCUMENT,
    )

    parsers: list[Any] = []
    seen_parser_ids: set[str] = set()
    interception_enabled = _slot_runtime_interception_enabled(resolved_settings)
    audit_sink = _slot_runtime_audit_sink(resolved_settings) if interception_enabled else None
    for contribution in contributions:
        manifest = _slot_manifest_for_contribution(slot_kernel, contribution)
        for parser in contribution.document_parsers:
            if parser.parser_id in seen_parser_ids:
                raise SlotConfigurationError(
                    f"duplicate document parser contribution: {parser.parser_id}"
                )
            seen_parser_ids.add(parser.parser_id)
            parsers.append(
                replace(
                    parser,
                    factory=_slot_scoped_factory(
                        parser.factory,
                        contribution.slot_id,
                        manifest.permissions,
                        enabled=interception_enabled,
                        audit_sink=audit_sink,
                    ),
                )
            )

    if not parsers:
        return None
    return ParserDispatcher(parsers, slot_context)


def build_slot_aware_data_source(
    *,
    settings: Any | None = None,
    preferred_source_id: str | None = None,
) -> Any:
    """Assemble a market data source registry from data slot contributions."""

    resolved_settings = settings if settings is not None else get_settings()
    slot_context = SlotContext(
        settings=resolved_settings,
        feature_flags=_feature_flags(resolved_settings),
    )
    slot_kernel = build_builtin_slot_kernel(enforcement=_slot_enforcement_policy(resolved_settings), settings=resolved_settings)
    contributions = slot_kernel.resolve_contributions(slot_context, slot_type=SlotType.DATA)

    data_sources: list[Any] = []
    seen_source_ids: set[str] = set()
    interception_enabled = _slot_runtime_interception_enabled(resolved_settings)
    audit_sink = _slot_runtime_audit_sink(resolved_settings) if interception_enabled else None
    for contribution in contributions:
        manifest = _slot_manifest_for_contribution(slot_kernel, contribution)
        for data_source in contribution.data_sources:
            if data_source.source_id in seen_source_ids:
                raise SlotConfigurationError(
                    f"duplicate data source contribution: {data_source.source_id}"
                )
            seen_source_ids.add(data_source.source_id)
            data_sources.append(
                replace(
                    data_source,
                    factory=_slot_scoped_factory(
                        data_source.factory,
                        contribution.slot_id,
                        manifest.permissions,
                        enabled=interception_enabled,
                        audit_sink=audit_sink,
                        result_wrapper=lambda source, slot_id=contribution.slot_id, permissions=manifest.permissions: slot_scoped_object(
                            guard_network_port(
                                source,
                                enabled=interception_enabled,
                                audit_sink=audit_sink,
                                methods=("connect", "download_kline", "get_latest_market_date"),
                            ),
                            slot_id,
                            permissions,
                            enabled=interception_enabled,
                            audit_sink=audit_sink,
                        ),
                    ),
                )
            )

    if not data_sources:
        return None
    return DataSourceRegistry(
        data_sources,
        slot_context,
        preferred_source_id=preferred_source_id,
    )


def build_slot_aware_gateway_routes(
    target_app: Any,
    *,
    settings: Any | None = None,
) -> tuple[str, ...]:
    """Mount gateway routers contributed by enabled gateway slots."""

    resolved_settings = settings if settings is not None else get_settings()
    slot_context = SlotContext(
        settings=resolved_settings,
        feature_flags=_feature_flags(resolved_settings),
    )
    slot_kernel = build_builtin_slot_kernel(enforcement=_slot_enforcement_policy(resolved_settings), settings=resolved_settings)
    contributions = slot_kernel.resolve_contributions(
        slot_context,
        slot_type=SlotType.GATEWAY,
    )

    mounted: list[str] = []
    seen_router_ids: set[str] = set()
    interception_enabled = _slot_runtime_interception_enabled(resolved_settings)
    audit_sink = _slot_runtime_audit_sink(resolved_settings) if interception_enabled else None
    for contribution in contributions:
        manifest = _slot_manifest_for_contribution(slot_kernel, contribution)
        for route in contribution.routes:
            if route.router_id in seen_router_ids:
                raise SlotConfigurationError(
                    f"duplicate gateway route contribution: {route.router_id}"
                )
            seen_router_ids.add(route.router_id)
            with slot_permission_context(
                contribution.slot_id,
                manifest.permissions,
                enforce=interception_enabled,
                audit_sink=audit_sink,
            ):
                router = route.router_factory(slot_context)
            if router is None:
                raise SlotConfigurationError(
                    f"gateway route {route.router_id} returned no router"
                )
            target_app.include_router(
                router,
                prefix=route.prefix,
                tags=list(route.tags),
            )
            mounted.append(route.router_id)
    return tuple(mounted)


def build_slot_aware_eval_suites(
    *,
    settings: Any | None = None,
    root: Any | None = None,
) -> Any:
    """Assemble an eval suite registry from eval slot contributions."""

    resolved_settings = settings if settings is not None else get_settings()
    slot_context = SlotContext(
        settings=resolved_settings,
        feature_flags=_feature_flags(resolved_settings),
    )
    slot_kernel = build_builtin_slot_kernel(enforcement=_slot_enforcement_policy(resolved_settings), settings=resolved_settings)
    contributions = slot_kernel.resolve_contributions(slot_context, slot_type=SlotType.EVAL)

    eval_suites: list[Any] = []
    seen_suite_ids: set[str] = set()
    interception_enabled = _slot_runtime_interception_enabled(resolved_settings)
    audit_sink = _slot_runtime_audit_sink(resolved_settings) if interception_enabled else None
    for contribution in contributions:
        manifest = _slot_manifest_for_contribution(slot_kernel, contribution)
        for suite in contribution.eval_suites:
            if suite.suite_id in seen_suite_ids:
                raise SlotConfigurationError(
                    f"duplicate eval suite contribution: {suite.suite_id}"
                )
            seen_suite_ids.add(suite.suite_id)
            eval_suites.append(suite)

    if not eval_suites:
        return None
    return EvalSuiteRegistry(eval_suites, slot_context, root=root)


def build_slot_aware_ui_panels(
    *,
    settings: Any | None = None,
) -> Any:
    """Assemble a UI panel registry from UI slot contributions."""

    resolved_settings = settings if settings is not None else get_settings()
    slot_context = SlotContext(
        settings=resolved_settings,
        feature_flags=_feature_flags(resolved_settings),
    )
    slot_kernel = build_builtin_slot_kernel(enforcement=_slot_enforcement_policy(resolved_settings), settings=resolved_settings)
    contributions = slot_kernel.resolve_contributions(slot_context, slot_type=SlotType.UI)

    ui_panels: list[Any] = []
    seen_panel_ids: set[tuple[str, str]] = set()
    interception_enabled = _slot_runtime_interception_enabled(resolved_settings)
    audit_sink = _slot_runtime_audit_sink(resolved_settings) if interception_enabled else None
    for contribution in contributions:
        manifest = _slot_manifest_for_contribution(slot_kernel, contribution)
        with slot_permission_context(
            contribution.slot_id,
            manifest.permissions,
            enforce=interception_enabled,
            audit_sink=audit_sink,
        ):
            panels = tuple(contribution.ui_panels)
        for panel in panels:
            key = (panel.workspace, panel.panel_id)
            if key in seen_panel_ids:
                raise SlotConfigurationError(
                    f"duplicate UI panel contribution: {panel.workspace}.{panel.panel_id}"
                )
            seen_panel_ids.add(key)
            ui_panels.append(panel)

    if not ui_panels:
        return None
    return UIPanelRegistry(ui_panels)


def build_slot_status_rows(settings: Any | None = None) -> tuple[dict[str, Any], ...]:
    """Return read-only built-in slot status rows for CLI/API/operator surfaces.

    This intentionally reads manifests and feature flags only; it does not call
    ``slot.resolve`` and therefore does not construct tool services, models, DB
    adapters, or network clients.
    """

    resolved_settings = settings if settings is not None else get_settings()
    slot_context = SlotContext(
        settings=resolved_settings,
        feature_flags=_feature_flags(resolved_settings),
    )
    slot_kernel = build_builtin_slot_kernel(enforcement=_slot_enforcement_policy(resolved_settings), settings=resolved_settings)
    status_by_id = {
        record.id: record
        for record in slot_kernel.status(slot_context)
    }
    return tuple(
        _slot_status_row(
            slot.manifest(),
            status_by_id[slot.manifest().id].status,
            health_status=status_by_id[slot.manifest().id].health,
        )
        for slot in slot_kernel.registry.all()
    )


def build_slot_bundle_rows(
    settings: Any | None = None,
    *,
    activation_repo: Any | None = None,
) -> tuple[dict[str, Any], ...]:
    """Return read-only built-in slot bundle rows for discovery surfaces."""

    resolved_settings = settings if settings is not None else get_settings()
    slot_context = SlotContext(
        settings=resolved_settings,
        feature_flags=_feature_flags(resolved_settings),
    )
    slot_kernel = build_builtin_slot_kernel(
        activation_repo=activation_repo,
        enforcement=_slot_enforcement_policy(resolved_settings),
        settings=resolved_settings,
    )
    active_bundle_id = (
        _active_bundle_activation(resolved_settings, activation_repo).bundle_id
        if resolved_settings.features.slot_loader
        else None
    )
    return tuple(
        _slot_bundle_row(record, active_bundle_id=active_bundle_id)
        for record in slot_kernel.bundle_status(slot_context)
    )


def build_slot_ui_panel_rows(
    settings: Any | None = None,
    *,
    workspace: str | None = None,
    zone: str | None = None,
    mode: str | None = None,
) -> tuple[dict[str, object], ...]:
    """Return read-only UI panel rows for Web/workspace discovery surfaces."""

    registry = build_slot_aware_ui_panels(settings=settings)
    if registry is None:
        return ()
    return registry.rows(workspace=workspace, zone=zone, mode=mode)


def _feature_flags(settings: Any) -> dict[str, bool]:
    return {
        feature_name: getattr(settings.features, feature_name)
        for feature_name in (f.name for f in fields(settings.features))
        if isinstance(getattr(settings.features, feature_name), bool)
    }


def _slot_enforcement_policy(settings: Any) -> SlotEnforcementPolicy:
    enabled = bool(getattr(settings.features, "slot_enforcement", False))
    return SlotEnforcementPolicy(
        enforce_permissions=enabled,
        enforce_health=enabled,
    )


def _slot_runtime_interception_enabled(settings: Any) -> bool:
    return bool(getattr(settings.features, "slot_runtime_interception", False))


def _slot_manifest_for_contribution(slot_kernel: SlotKernel, contribution: SlotContribution) -> Any:
    return slot_kernel.registry.get(contribution.slot_id).manifest()


def _slot_runtime_audit_sink(settings: Any) -> Any:
    def _append(event: SlotAccessEvent) -> None:
        try:
            _governance_repo_for_settings(settings).append_audit_event(
                EnterpriseAuditEvent(
                    event_type="slot_permission_violation",
                    tenant_id="local",
                    actor_hash="slot-runtime-interception",
                    resource_type=event.resource_type,
                    resource_id=event.slot_id,
                    metadata={
                        "slot_id": event.slot_id,
                        "declared": event.declared,
                        "attempted": event.attempted,
                        "action": event.action,
                    },
                )
            )
        except Exception:
            pass

    return _append


def _slot_scoped_factory(
    factory: Any,
    slot_id: str,
    permissions: Any,
    *,
    enabled: bool,
    audit_sink: Any,
    result_wrapper: Any | None = None,
) -> Any:
    def _factory(context: SlotContext) -> Any:
        if enabled:
            with slot_permission_context(
                slot_id,
                permissions,
                enforce=True,
                audit_sink=audit_sink,
            ):
                result = factory(context)
        else:
            result = factory(context)
        if result_wrapper is not None:
            return result_wrapper(result)
        return result

    return _factory


def _slot_install_policy(
    settings: Any,
    *,
    secret_provider: Any | None = None,
    signing_repo: Any | None = None,
) -> SlotInstallPolicy:
    trusted_publisher_keys = _slot_trusted_publisher_keys(
        settings,
        secret_provider=secret_provider,
    )
    return SlotInstallPolicy(
        auth_mode=settings.auth.mode,
        allow_unsigned_local=settings.slots.allow_unsigned_local,
        enterprise_allowlist=settings.slots.enterprise_allowlist,
        trusted_signers=settings.slots.trusted_signers,
        trusted_publisher_keys=trusted_publisher_keys,
        signing_repository=(
            _slot_signing_repo_for_settings(settings, signing_repo)
            if signing_repo is not None or trusted_publisher_keys
            else None
        ),
    )


def _slot_trusted_publisher_keys(
    settings: Any,
    *,
    secret_provider: Any | None = None,
) -> dict[str, str]:
    keys = dict(settings.slots.trusted_publisher_keys)
    provider = secret_provider
    if provider is None:
        try:
            from doge.bootstrap.gateway_factories.secrets import build_secret_provider

            provider = build_secret_provider()
        except Exception:  # noqa: BLE001 - optional trust-source bridge only
            provider = None
    if provider is not None:
        secret_value = provider.get_secret("slot.trusted_publisher_keys")
        keys.update(parse_slot_trusted_publisher_keys(secret_value))
    return keys


def _slot_signing_repo_for_settings(settings: Any, signing_repo: Any | None = None) -> Any:
    if signing_repo is not None:
        return signing_repo
    from doge.infrastructure.database.slot_signing_repository import (
        SQLiteSlotSigningRepository,
    )

    return SQLiteSlotSigningRepository(settings.db.agent_db)


def _activation_repo_for_settings(settings: Any, activation_repo: Any | None = None) -> Any:
    if activation_repo is not None:
        return activation_repo
    from doge.infrastructure.database.slot_activation_repository import (
        SQLiteSlotActivationRepository,
    )

    return SQLiteSlotActivationRepository(settings.db.agent_db)


def _governance_repo_for_settings(settings: Any, governance_repo: Any | None = None) -> Any:
    if governance_repo is not None:
        return governance_repo
    from doge.infrastructure.database.enterprise_governance import (
        SQLiteEnterpriseGovernanceRepository,
    )

    return SQLiteEnterpriseGovernanceRepository(settings.db.agent_db)


def _active_bundle_activation(settings: Any, activation_repo: Any | None = None):
    if not settings.features.slot_loader:
        return _SLOT_BUNDLE_ACTIVATION.replace(bundle_id=None)
    record = _activation_repo_for_settings(settings, activation_repo).get_active()
    return _SLOT_BUNDLE_ACTIVATION.replace(
        bundle_id=record.bundle_id,
        activated_at=record.activated_at,
        actor_hash=record.actor_hash,
    )


def _append_slot_bundle_audit(
    action: str,
    bundle_id: str,
    *,
    settings: Any,
    governance_repo: Any | None,
    actor_hash: str,
    tenant_id: str,
    request_id: str | None,
) -> None:
    repo = _governance_repo_for_settings(settings, governance_repo)
    repo.append_audit_event(
        EnterpriseAuditEvent(
            event_type=f"slot_bundle_{action}",
            tenant_id=tenant_id,
            actor_hash=actor_hash,
            resource_type="slot_bundle",
            resource_id=bundle_id,
            request_id=request_id,
            metadata={"action": action},
        )
    )


def _build_builtin_slot_registry_for_settings(settings: Any) -> SlotRegistry:
    if signature(build_builtin_slot_registry).parameters:
        return build_builtin_slot_registry(settings)
    return build_builtin_slot_registry()


def _slot_manifest_tool_names(slot_kernel: SlotKernel) -> tuple[str, ...]:
    return tuple(
        tool_name
        for slot in slot_kernel.registry.all()
        if slot.manifest().type is SlotType.TOOL
        for tool_name in slot.manifest().provides.tools
    )


def _bundles_supported_by(registry: SlotRegistry) -> tuple[SlotBundle, ...]:
    known = {manifest.id for manifest in registry.manifests()}
    supported: list[SlotBundle] = []
    for bundle in _BUILTIN_SLOT_BUNDLES:
        required = set(bundle.slot_ids) | set(bundle.disabled_slot_ids)
        if required <= known:
            supported.append(bundle)
    return tuple(supported)


def _register_manifest_only_slots(registry: SlotRegistry, settings: Any) -> None:
    if not getattr(settings.features, "slot_loader", False):
        return
    manifest_dirs = list(getattr(settings.slots, "manifest_dirs", ()))
    install_dir = getattr(settings.slots, "install_dir", None)
    if getattr(settings.features, "slot_install", False) and install_dir is not None:
        install_path = Path(install_dir)
        if install_path.exists():
            manifest_dirs.append(install_path)
    if not manifest_dirs:
        return
    for slot in SlotLoader().load(manifest_dirs):
        registry.register(slot)


def _find_bundle(bundle_id: str, bundles: tuple[SlotBundle, ...]) -> SlotBundle:
    for bundle in bundles:
        if bundle.id == bundle_id:
            return bundle
    raise UnknownSlotError(f"unknown slot bundle: {bundle_id}")


def _find_bundle_row(bundle_id: str, rows: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    for row in rows:
        if row["id"] == bundle_id:
            return row
    raise UnknownSlotError(f"unknown slot bundle: {bundle_id}")


def _resolve_contributions_of_type(
    registry: SlotRegistry,
    context: SlotContext,
    slot_type: SlotType,
) -> tuple[SlotContribution, ...]:
    return SlotKernel(registry).resolve_contributions(context, slot_type=slot_type)


def _flags_satisfied(feature_flags: tuple[str, ...], context: SlotContext) -> bool:
    for flag in feature_flags:
        if not context.feature_flags.get(flag, False):
            return False
    return True


def _slot_status_row(
    manifest: Any,
    status: str,
    *,
    health_status: str | None = None,
) -> dict[str, Any]:
    return {
        "id": manifest.id,
        "name": manifest.name,
        "version": manifest.version,
        "type": manifest.type.value,
        "owner": manifest.owner,
        "maturity": manifest.maturity,
        "description": manifest.description,
        "entrypoint": manifest.entrypoint,
        "status": status,
        "feature_flags": list(manifest.feature_flags),
        "provides": {
            "tools": list(manifest.provides.tools),
            "capabilities": list(manifest.provides.capabilities),
            "metadata": dict(manifest.provides.metadata),
        },
        "requires": [
            {
                "kind": requirement.kind,
                "id": requirement.id,
                "optional": requirement.optional,
            }
            for requirement in manifest.requires
        ],
        "permissions": {
            "filesystem": manifest.permissions.filesystem,
            "network": manifest.permissions.network,
            "shell": manifest.permissions.shell,
            "database": manifest.permissions.database,
            "secrets": list(manifest.permissions.secrets),
            "risk_level": manifest.permissions.risk_level,
        },
        "health": {
            "status": health_status or manifest.health.status,
            "notes": manifest.health.notes,
        },
        "compatibility": {
            "runtime_min": manifest.compatibility.runtime_min,
            "replaces": list(manifest.compatibility.replaces),
            "breaking": manifest.compatibility.breaking,
        },
        "counts": {
            "tools": len(manifest.provides.tools),
            "capabilities": len(manifest.provides.capabilities),
        },
    }


def _slot_bundle_row(record: Any, *, active_bundle_id: str | None = None) -> dict[str, Any]:
    return {
        "id": record.id,
        "name": record.name,
        "description": record.description,
        "active": record.id == active_bundle_id,
        "status": record.status,
        "slot_ids": list(record.slot_ids),
        "enabled_slot_ids": list(record.enabled_slot_ids),
        "disabled_slot_ids": list(record.disabled_slot_ids),
        "missing_slot_ids": list(record.missing_slot_ids),
        "maturity": record.maturity,
        "counts": {
            "slots": len(record.slot_ids),
            "enabled": len(record.enabled_slot_ids),
            "disabled": len(record.disabled_slot_ids),
            "missing": len(record.missing_slot_ids),
        },
    }

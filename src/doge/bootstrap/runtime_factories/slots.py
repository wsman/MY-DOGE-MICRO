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

from dataclasses import fields
from typing import Any

from doge.application.tools.registry import ToolRegistry
from doge.bootstrap.runtime_factories.builtin_model_slot import ModelKimiAgentSdkSlot
from doge.config import get_settings
from doge.platform.slots import (
    SLOT_SERVICE_SECRET_PROVIDER,
    SlotConfigurationError,
    SlotContribution,
    SlotContext,
    SlotRegistry,
    SlotType,
)
from doge.products.market.slot import MarketCoreSlot


def build_builtin_slot_registry() -> SlotRegistry:
    """Construct the registry of built-in slots."""
    registry = SlotRegistry()
    registry.register(MarketCoreSlot())
    registry.register(ModelKimiAgentSdkSlot())
    return registry


def build_slot_aware_tool_registry(
    gateway_container_fn: Any,
    *,
    entitlement_checker: Any = None,
    context: Any = None,
) -> ToolRegistry:
    """Assemble a ``ToolRegistry`` from slot contributions + remaining descriptors.

    Slot-owned descriptors are registered first via the same
    ``include_descriptors`` seam the legacy factory uses (against the same
    service), then the remaining descriptors are registered so nothing is
    double-registered (``ToolRegistry.register`` appends to ``self.schemas``
    without dedup).
    """
    service = gateway_container_fn().build_tool_application_service()
    settings = get_settings()

    slot_context = SlotContext(
        settings=settings,
        feature_flags=_feature_flags(settings),
        tool_application_service=service,
    )

    slot_registry = build_builtin_slot_registry()
    contributions = _resolve_contributions_of_type(
        slot_registry,
        slot_context,
        SlotType.TOOL,
    )

    registry = ToolRegistry(entitlement_checker=entitlement_checker, context=context)
    slot_owned: set[str] = set()
    for contribution in contributions:
        if not contribution.tools:
            continue
        if contribution.executor is None:
            raise SlotConfigurationError(
                f"slot {contribution.slot_id} contributed tools without an executor"
            )
        registry.include_descriptors(contribution.tools, contribution.executor)
        slot_owned.update(descriptor.name for descriptor in contribution.tools)

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
) -> dict[str, Any]:
    """Assemble agent backends from model slot contributions."""

    if secret_provider is None:
        secret_provider = gateway_container_fn().build_secret_provider()
    settings = get_settings()
    slot_context = SlotContext(
        settings=settings,
        feature_flags=_feature_flags(settings),
        service_locator=lambda service_id: (
            secret_provider if service_id == SLOT_SERVICE_SECRET_PROVIDER else None
        ),
    )
    slot_registry = build_builtin_slot_registry()
    contributions = _resolve_contributions_of_type(
        slot_registry,
        slot_context,
        SlotType.MODEL,
    )

    backends: dict[str, Any] = {}
    for contribution in contributions:
        for backend in contribution.model_backends:
            if backend.backend_id in backends:
                raise SlotConfigurationError(
                    f"duplicate model backend contribution: {backend.backend_id}"
                )
            backends[backend.backend_id] = backend.factory(slot_context)
    return backends


def _feature_flags(settings: Any) -> dict[str, bool]:
    return {
        feature_name: getattr(settings.features, feature_name)
        for feature_name in (f.name for f in fields(settings.features))
        if isinstance(getattr(settings.features, feature_name), bool)
    }


def _resolve_contributions_of_type(
    registry: SlotRegistry,
    context: SlotContext,
    slot_type: SlotType,
) -> tuple[SlotContribution, ...]:
    contributions: list[SlotContribution] = []
    for slot in registry.all():
        manifest = slot.manifest()
        if manifest.type is not slot_type:
            continue
        if not _flags_satisfied(manifest.feature_flags, context):
            continue
        contributions.append(slot.resolve(context))
    return tuple(contributions)


def _flags_satisfied(feature_flags: tuple[str, ...], context: SlotContext) -> bool:
    for flag in feature_flags:
        if not context.feature_flags.get(flag, False):
            return False
    return True

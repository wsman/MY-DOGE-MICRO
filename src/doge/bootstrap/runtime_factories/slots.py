"""Slot-aware tool registry wiring (ADR-0042, Sprint 033).

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
from doge.config import get_settings
from doge.platform.slots import SlotContext, SlotRegistry
from doge.products.market.slot import MarketCoreSlot


def build_builtin_slot_registry() -> SlotRegistry:
    """Construct the registry of built-in slots for Sprint 033."""
    registry = SlotRegistry()
    registry.register(MarketCoreSlot())
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

    feature_flags = {
        feature_name: getattr(settings.features, feature_name)
        for feature_name in (f.name for f in fields(settings.features))
        if isinstance(getattr(settings.features, feature_name), bool)
    }
    slot_context = SlotContext(
        settings=settings,
        feature_flags=feature_flags,
        tool_application_service=service,
    )

    slot_registry = build_builtin_slot_registry()
    contributions = slot_registry.resolve_contributions(slot_context)

    registry = ToolRegistry(entitlement_checker=entitlement_checker, context=context)
    slot_owned: set[str] = set()
    for contribution in contributions:
        registry.include_descriptors(contribution.tools, contribution.executor)
        slot_owned.update(descriptor.name for descriptor in contribution.tools)

    remaining = tuple(
        descriptor
        for descriptor in service.tool_descriptors()
        if descriptor.name not in slot_owned
    )
    registry.include_descriptors(remaining, service)
    return registry

"""Runtime factory helpers for agent tool registry wiring."""

from __future__ import annotations

from typing import Any

from doge.application.tools.factory import build_default_tool_registry as _build_tool_registry
from doge.config import get_settings


def build_default_tool_registry(gateway_container_fn, *, entitlement_checker: Any = None, context: Any = None):
    # ADR-0042 Slot Platform (Sprint 033): when the slot feature flag is on, the
    # default registry is assembled from slot contributions plus the remaining
    # descriptors. The flag-off branch is behaviorally identical to the legacy
    # factory (it only adds one settings read before delegating).
    if get_settings().features.slot_platform:
        from doge.bootstrap.runtime_factories.slots import build_slot_aware_tool_registry

        return build_slot_aware_tool_registry(
            gateway_container_fn,
            entitlement_checker=entitlement_checker,
            context=context,
        )
    return _build_tool_registry(
        service=gateway_container_fn().build_tool_application_service(),
        entitlement_checker=entitlement_checker,
        context=context,
    )

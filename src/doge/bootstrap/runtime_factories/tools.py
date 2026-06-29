"""Runtime factory helpers for agent tool registry wiring."""

from __future__ import annotations

from typing import Any

from doge.application.tools.factory import build_default_tool_registry as _build_tool_registry


def build_default_tool_registry(gateway_container_fn, *, entitlement_checker: Any = None, context: Any = None):
    return _build_tool_registry(
        service=gateway_container_fn().build_tool_application_service(),
        entitlement_checker=entitlement_checker,
        context=context,
    )

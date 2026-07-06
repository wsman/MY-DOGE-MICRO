"""SlotContext controlled-facade tests.

The context must expose only controlled services and must not leak container or
infrastructure handles to slot implementations.
"""

from __future__ import annotations

import pytest

from doge.platform.slots import SlotConfigurationError, SlotContext

_FORBIDDEN_ATTRS = (
    "app_container",
    "runtime_container",
    "gateway_container",
    "bootstrap",
    "infrastructure",
    "workspace_container",
)


def test_context_exposes_only_controlled_services(slot_context_factory, stub_service) -> None:
    ctx = slot_context_factory()
    assert ctx.tool_application_service is stub_service
    assert isinstance(ctx.feature_flags, dict)
    assert ctx.feature_flags == {"slot_platform": True}
    # settings/audit/permission_checker are present (settings is untyped Any)
    assert ctx.audit is None
    assert ctx.permission_checker is None
    _ = ctx.settings  # accessible


@pytest.mark.parametrize("attr", _FORBIDDEN_ATTRS)
def test_context_has_no_container_or_infrastructure_attrs(slot_context_factory, attr) -> None:
    ctx = slot_context_factory()
    assert not hasattr(ctx, attr), f"SlotContext must not expose {attr!r}"


def test_locate_without_locator_raises(slot_context_factory) -> None:
    ctx = slot_context_factory()
    with pytest.raises(SlotConfigurationError):
        ctx.locate("anything")


def test_locate_with_locator_delegates(slot_context_factory) -> None:
    # Arrange
    sentinel = object()
    base = slot_context_factory()
    ctx = SlotContext(
        settings=base.settings,
        feature_flags=base.feature_flags,
        tool_application_service=base.tool_application_service,
        service_locator=lambda service_id: sentinel if service_id == "x" else None,
    )
    # Act / Assert
    assert ctx.locate("x") is sentinel
    with pytest.raises(SlotConfigurationError):
        ctx.locate("missing")


def test_locate_wraps_locator_exceptions(slot_context_factory) -> None:
    def _raising(_service_id: str):
        raise RuntimeError("boom")

    base = slot_context_factory()
    ctx = SlotContext(
        settings=base.settings,
        feature_flags=base.feature_flags,
        tool_application_service=base.tool_application_service,
        service_locator=_raising,
    )
    with pytest.raises(SlotConfigurationError):
        ctx.locate("x")

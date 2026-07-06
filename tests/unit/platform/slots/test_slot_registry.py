"""SlotRegistry behavior tests."""

from __future__ import annotations

import pytest

from doge.platform.slots import (
    SlotAlreadyRegisteredError,
    SlotRegistry,
    UnknownSlotError,
)


def test_register_preserves_order(stub_slot, second_stub_slot) -> None:
    # Arrange
    registry = SlotRegistry()
    # Act
    registry.register(stub_slot)
    registry.register(second_stub_slot)
    # Assert
    assert [s.manifest().id for s in registry.all()] == ["market.core", "other.slot"]


def test_duplicate_register_raises(stub_slot) -> None:
    registry = SlotRegistry()
    registry.register(stub_slot)
    with pytest.raises(SlotAlreadyRegisteredError):
        registry.register(stub_slot)


def test_unknown_get_raises() -> None:
    registry = SlotRegistry()
    with pytest.raises(UnknownSlotError):
        registry.get("nope")


def test_unregister_removes_slot(stub_slot) -> None:
    registry = SlotRegistry()
    registry.register(stub_slot)
    registry.unregister("market.core")
    with pytest.raises(UnknownSlotError):
        registry.get("market.core")


def test_unregister_unknown_raises() -> None:
    registry = SlotRegistry()
    with pytest.raises(UnknownSlotError):
        registry.unregister("nope")


def test_resolve_flag_on_returns_contributions(stub_slot, slot_context_factory) -> None:
    registry = SlotRegistry()
    registry.register(stub_slot)
    contributions = registry.resolve_contributions(slot_context_factory({"slot_platform": True}))
    assert len(contributions) == 1
    assert contributions[0].slot_id == "market.core"
    assert [d.name for d in contributions[0].tools] == ["query_stock", "stock_overview"]


def test_resolve_flag_off_returns_none(stub_slot, slot_context_factory) -> None:
    registry = SlotRegistry()
    registry.register(stub_slot)
    contributions = registry.resolve_contributions(slot_context_factory({"slot_platform": False}))
    assert contributions == ()


def test_status_reports_disabled_when_flag_off(stub_slot, slot_context_factory) -> None:
    registry = SlotRegistry()
    registry.register(stub_slot)
    statuses = registry.status(slot_context_factory({"slot_platform": False}))
    assert len(statuses) == 1
    assert statuses[0].status == "disabled"
    assert statuses[0].id == "market.core"


def test_status_reports_resolved_when_flag_on(stub_slot, slot_context_factory) -> None:
    registry = SlotRegistry()
    registry.register(stub_slot)
    statuses = registry.status(slot_context_factory({"slot_platform": True}))
    assert statuses[0].status == "resolved"
    assert statuses[0].tools_count == 2


def test_status_without_context_is_registered(stub_slot) -> None:
    registry = SlotRegistry()
    registry.register(stub_slot)
    assert registry.status()[0].status == "registered"

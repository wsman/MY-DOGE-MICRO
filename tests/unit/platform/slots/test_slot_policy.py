from __future__ import annotations

import pytest

from doge.platform.slots import SlotConfigurationError, SlotPolicy


def test_policy_allows_when_feature_flags_are_satisfied(stub_slot, slot_context_factory) -> None:
    policy = SlotPolicy()

    assert policy.allows(
        stub_slot.manifest(),
        slot_context_factory({"slot_platform": True}),
    )


def test_policy_denies_when_feature_flag_is_off(stub_slot, slot_context_factory) -> None:
    policy = SlotPolicy()

    assert not policy.allows(
        stub_slot.manifest(),
        slot_context_factory({"slot_platform": False}),
    )


def test_policy_disable_list_wins(stub_slot, slot_context_factory) -> None:
    policy = SlotPolicy(disabled_slots=("market.core",))

    assert not policy.allows(
        stub_slot.manifest(),
        slot_context_factory({"slot_platform": True}),
    )


def test_policy_enabled_list_excludes_other_slots(stub_slot, slot_context_factory) -> None:
    policy = SlotPolicy(enabled_slots=("other.slot",))

    assert not policy.allows(
        stub_slot.manifest(),
        slot_context_factory({"slot_platform": True}),
    )


def test_policy_can_ignore_feature_flags_for_static_diagnostics(
    stub_slot,
    slot_context_factory,
) -> None:
    policy = SlotPolicy(enforce_feature_flags=False)

    assert policy.allows(
        stub_slot.manifest(),
        slot_context_factory({"slot_platform": False}),
    )


def test_policy_rejects_enable_disable_overlap() -> None:
    with pytest.raises(SlotConfigurationError, match="both enable and disable"):
        SlotPolicy(enabled_slots=("market.core",), disabled_slots=("market.core",))

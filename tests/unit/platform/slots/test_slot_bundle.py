from __future__ import annotations

import pytest

from doge.platform.slots import SlotBundle, SlotConfigurationError, SlotPolicy


def test_bundle_requires_bundle_prefix() -> None:
    with pytest.raises(SlotConfigurationError, match="must start with bundle"):
        SlotBundle(
            id="local",
            name="Local",
            description="Local bundle",
            slot_ids=("market.core",),
        )


def test_bundle_requires_slots() -> None:
    with pytest.raises(SlotConfigurationError, match="at least one slot"):
        SlotBundle(
            id="bundle.local",
            name="Local",
            description="Local bundle",
            slot_ids=(),
        )


def test_bundle_rejects_enabled_disabled_overlap() -> None:
    with pytest.raises(SlotConfigurationError, match="cannot include disabled"):
        SlotBundle(
            id="bundle.local",
            name="Local",
            description="Local bundle",
            slot_ids=("market.core",),
            disabled_slot_ids=("market.core",),
        )


def test_policy_from_bundle_uses_bundle_slot_sets() -> None:
    bundle = SlotBundle(
        id="bundle.local",
        name="Local",
        description="Local bundle",
        slot_ids=("market.core",),
        disabled_slot_ids=("other.slot",),
    )

    policy = SlotPolicy.from_bundle(bundle)

    assert policy.enabled_slots == ("market.core",)
    assert policy.disabled_slots == ("other.slot",)

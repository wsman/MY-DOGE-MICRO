from __future__ import annotations

import pytest

from doge.platform.slots import (
    SlotBundle,
    SlotBundleActivationState,
    SlotConfigurationError,
    policy_for_activation,
)


def test_activation_state_tracks_active_bundle() -> None:
    state = SlotBundleActivationState()
    bundle = SlotBundle(
        id="bundle.local",
        name="Local",
        description="Local bundle",
        slot_ids=("market.core",),
    )

    activation = state.activate(bundle)

    assert activation.active is True
    assert activation.bundle_id == "bundle.local"
    assert state.current().bundle_id == "bundle.local"
    assert state.clear().active is False


def test_activation_state_can_load_persisted_record() -> None:
    state = SlotBundleActivationState()

    activation = state.replace(
        bundle_id="bundle.local",
        activated_at="2026-07-08T00:00:00Z",
        actor_hash="actor-a",
    )

    assert activation.bundle_id == "bundle.local"
    assert activation.activated_at == "2026-07-08T00:00:00Z"
    assert activation.actor_hash == "actor-a"
    assert state.current() == activation


def test_policy_for_activation_uses_bundle_slot_sets() -> None:
    bundle = SlotBundle(
        id="bundle.local",
        name="Local",
        description="Local bundle",
        slot_ids=("market.core",),
        disabled_slot_ids=("model.demo",),
    )
    state = SlotBundleActivationState()
    activation = state.activate(bundle)

    policy = policy_for_activation(activation, (bundle,))

    assert policy.enabled_slots == ("market.core",)
    assert policy.disabled_slots == ("model.demo",)


def test_policy_for_unknown_active_bundle_fails_fast() -> None:
    state = SlotBundleActivationState()
    state.activate(
        SlotBundle(
            id="bundle.local",
            name="Local",
            description="Local bundle",
            slot_ids=("market.core",),
        )
    )

    with pytest.raises(SlotConfigurationError, match="active slot bundle"):
        policy_for_activation(state.current(), ())

"""Slot bundle activation state."""

from __future__ import annotations

from dataclasses import dataclass
from threading import RLock

from doge.platform.slots.bundles import SlotBundle
from doge.platform.slots.errors import SlotConfigurationError
from doge.platform.slots.policy import SlotPolicy


@dataclass(frozen=True)
class SlotBundleActivation:
    """Current bundle activation record."""

    bundle_id: str | None = None
    activated_at: str | None = None
    actor_hash: str | None = None

    @property
    def active(self) -> bool:
        return self.bundle_id is not None


class SlotBundleActivationState:
    """Small mutable holder used as a bundle activation cache."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._bundle_id: str | None = None
        self._activated_at: str | None = None
        self._actor_hash: str | None = None

    def current(self) -> SlotBundleActivation:
        with self._lock:
            return SlotBundleActivation(self._bundle_id, self._activated_at, self._actor_hash)

    def activate(
        self,
        bundle: SlotBundle,
        *,
        activated_at: str | None = None,
        actor_hash: str | None = None,
    ) -> SlotBundleActivation:
        with self._lock:
            self._bundle_id = bundle.id
            self._activated_at = activated_at
            self._actor_hash = actor_hash
            return SlotBundleActivation(self._bundle_id, self._activated_at, self._actor_hash)

    def replace(
        self,
        *,
        bundle_id: str | None,
        activated_at: str | None = None,
        actor_hash: str | None = None,
    ) -> SlotBundleActivation:
        with self._lock:
            self._bundle_id = bundle_id
            self._activated_at = activated_at
            self._actor_hash = actor_hash
            return SlotBundleActivation(self._bundle_id, self._activated_at, self._actor_hash)

    def clear(self) -> SlotBundleActivation:
        with self._lock:
            self._bundle_id = None
            self._activated_at = None
            self._actor_hash = None
            return SlotBundleActivation()


def policy_for_activation(
    activation: SlotBundleActivation,
    bundles: tuple[SlotBundle, ...],
) -> SlotPolicy:
    """Return a policy constrained by the active bundle, if one exists."""

    if activation.bundle_id is None:
        return SlotPolicy()
    for bundle in bundles:
        if bundle.id == activation.bundle_id:
            return SlotPolicy.from_bundle(bundle)
    raise SlotConfigurationError(f"active slot bundle is not registered: {activation.bundle_id}")

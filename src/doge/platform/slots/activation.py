"""Process-local slot bundle activation state."""

from __future__ import annotations

from dataclasses import dataclass
from threading import RLock

from doge.platform.slots.bundles import SlotBundle
from doge.platform.slots.errors import SlotConfigurationError
from doge.platform.slots.policy import SlotPolicy


@dataclass(frozen=True)
class SlotBundleActivation:
    """Current process-local bundle activation record."""

    bundle_id: str | None = None

    @property
    def active(self) -> bool:
        return self.bundle_id is not None


class SlotBundleActivationState:
    """Small mutable holder for local-alpha bundle activation.

    This is intentionally process-local. Sprint 046 does not add persistence or
    cross-process synchronization.
    """

    def __init__(self) -> None:
        self._lock = RLock()
        self._bundle_id: str | None = None

    def current(self) -> SlotBundleActivation:
        with self._lock:
            return SlotBundleActivation(self._bundle_id)

    def activate(self, bundle: SlotBundle) -> SlotBundleActivation:
        with self._lock:
            self._bundle_id = bundle.id
            return SlotBundleActivation(self._bundle_id)

    def clear(self) -> SlotBundleActivation:
        with self._lock:
            self._bundle_id = None
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

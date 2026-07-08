"""Port for persisted Slot Platform bundle activation state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SlotActivationRecord:
    """Persisted active bundle pointer."""

    bundle_id: str | None = None
    activated_at: str | None = None
    actor_hash: str | None = None

    @property
    def active(self) -> bool:
        return self.bundle_id is not None


class ISlotActivationRepository(Protocol):
    """Repository for the single active slot bundle pointer."""

    def get_active(self) -> SlotActivationRecord:
        ...

    def set_active(self, bundle_id: str, actor_hash: str) -> SlotActivationRecord:
        ...

    def clear(self) -> SlotActivationRecord:
        ...

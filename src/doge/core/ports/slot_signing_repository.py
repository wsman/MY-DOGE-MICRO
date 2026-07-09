"""Port for Slot Platform signing-key revocation state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SlotSignerRevocation:
    """Persisted revoked slot-signing publisher key."""

    key_id: str
    revoked_at: str
    reason: str | None = None
    actor_hash: str | None = None
    successor_key_id: str | None = None


class ISlotSigningRepository(Protocol):
    """Repository for revoked slot publisher signing keys."""

    def is_revoked(self, key_id: str) -> bool:
        ...

    def revoke(
        self,
        key_id: str,
        *,
        reason: str | None = None,
        actor_hash: str | None = None,
        successor_key_id: str | None = None,
    ) -> SlotSignerRevocation:
        ...

    def list_revoked(self) -> tuple[SlotSignerRevocation, ...]:
        ...

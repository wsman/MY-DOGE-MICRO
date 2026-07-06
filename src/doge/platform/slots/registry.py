"""Slot registry: aggregates slot contributions for runtime assembly.

The registry holds :class:`~doge.platform.slots.contracts.ISlot` instances keyed
by manifest id. :meth:`SlotRegistry.resolve_contributions` returns contributions
only for slots whose declared feature flags are all satisfied by the context;
slots whose flags are unsatisfied are skipped and reported as ``disabled`` by
:meth:`SlotRegistry.status`.

The registry never reads ``os.environ`` directly: it consumes an already-resolved
feature-flag map from the :class:`~doge.platform.slots.contracts.SlotContext`
supplied by the bootstrap layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from doge.platform.slots.contracts import (
    ISlot,
    SlotContribution,
    SlotContext,
    SlotStatus,
)
from doge.platform.slots.errors import SlotAlreadyRegisteredError, UnknownSlotError
from doge.platform.slots.manifest import SlotManifest


@dataclass(frozen=True)
class SlotStatusRecord:
    """A single slot's status row for CLI/diagnostics output."""

    id: str
    name: str
    type: str
    status: str  # SlotStatus value
    tools_count: int
    health: str
    feature_flags: tuple[str, ...]


class SlotRegistry:
    """Registry of slot contributions, keyed by manifest id."""

    def __init__(self) -> None:
        self._slots: dict[str, ISlot] = {}

    def register(self, slot: ISlot) -> None:
        """Register a slot; raise on duplicate id."""
        slot_id = slot.manifest().id
        if slot_id in self._slots:
            raise SlotAlreadyRegisteredError(f"slot already registered: {slot_id}")
        self._slots[slot_id] = slot

    def unregister(self, slot_id: str) -> None:
        """Remove a registered slot by id; raise if absent."""
        if slot_id not in self._slots:
            raise UnknownSlotError(f"unknown slot: {slot_id}")
        del self._slots[slot_id]

    def get(self, slot_id: str) -> ISlot:
        """Return the slot for ``slot_id``; raise if absent."""
        if slot_id not in self._slots:
            raise UnknownSlotError(f"unknown slot: {slot_id}")
        return self._slots[slot_id]

    def all(self) -> tuple[ISlot, ...]:
        """Return all registered slots in registration order."""
        return tuple(self._slots.values())

    def manifests(self) -> tuple[SlotManifest, ...]:
        """Return all slot manifests in registration order."""
        return tuple(slot.manifest() for slot in self._slots.values())

    def status(self, context: Optional[SlotContext] = None) -> list[SlotStatusRecord]:
        """Return status rows for all slots.

        Without a context every slot is ``registered``. With a context, a slot
        whose feature flags are all satisfied is ``resolved``; otherwise
        ``disabled``.
        """
        records: list[SlotStatusRecord] = []
        for slot in self._slots.values():
            manifest = slot.manifest()
            if context is None:
                status = SlotStatus.REGISTERED.value
            elif _flags_satisfied(manifest, context):
                status = SlotStatus.RESOLVED.value
            else:
                status = SlotStatus.DISABLED.value
            records.append(
                SlotStatusRecord(
                    id=manifest.id,
                    name=manifest.name,
                    type=manifest.type.value,
                    status=status,
                    tools_count=len(manifest.provides.tools),
                    health=manifest.health.status,
                    feature_flags=manifest.feature_flags,
                )
            )
        return records

    def resolve_contributions(self, context: SlotContext) -> tuple[SlotContribution, ...]:
        """Resolve contributions for slots whose feature flags are satisfied.

        Slots whose declared feature flags are not all true in
        ``context.feature_flags`` are skipped (no contribution) but remain
        registered and appear in :meth:`status` as ``disabled``.
        """
        contributions: list[SlotContribution] = []
        for slot in self._slots.values():
            manifest = slot.manifest()
            if not _flags_satisfied(manifest, context):
                continue
            contributions.append(slot.resolve(context))
        return tuple(contributions)


def _flags_satisfied(manifest: SlotManifest, context: SlotContext) -> bool:
    """Return True iff every declared feature flag is true in the context."""
    for flag in manifest.feature_flags:
        if not context.feature_flags.get(flag, False):
            return False
    return True

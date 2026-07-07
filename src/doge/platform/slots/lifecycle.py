"""Slot lifecycle helper."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from doge.platform.slots.contracts import ISlot, SlotContext
from doge.platform.slots.errors import SlotConfigurationError


class SlotLifecycleState(str, Enum):
    """Lifecycle state tracked by ``SlotKernel``."""

    REGISTERED = "registered"
    STARTED = "started"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass(frozen=True)
class SlotLifecycleRecord:
    """Lifecycle state for a single slot."""

    slot_id: str
    state: SlotLifecycleState
    error: str = ""


class SlotLifecycle:
    """Invoke slot start/stop hooks once and record local state."""

    def __init__(self) -> None:
        self._records: dict[str, SlotLifecycleRecord] = {}
        self._started_order: list[str] = []

    def record_for(self, slot_id: str) -> SlotLifecycleRecord:
        return self._records.get(
            slot_id,
            SlotLifecycleRecord(slot_id=slot_id, state=SlotLifecycleState.REGISTERED),
        )

    def started_slot_ids(self) -> tuple[str, ...]:
        return tuple(self._started_order)

    def start(self, slot: ISlot, context: SlotContext) -> SlotLifecycleRecord:
        slot_id = slot.manifest().id
        if self.record_for(slot_id).state is SlotLifecycleState.STARTED:
            return self.record_for(slot_id)
        try:
            slot.start(context)
        except Exception as exc:  # lifecycle errors must surface as slot errors
            record = SlotLifecycleRecord(
                slot_id=slot_id,
                state=SlotLifecycleState.ERROR,
                error=str(exc),
            )
            self._records[slot_id] = record
            raise SlotConfigurationError(f"slot {slot_id} failed to start: {exc}") from exc
        record = SlotLifecycleRecord(slot_id=slot_id, state=SlotLifecycleState.STARTED)
        self._records[slot_id] = record
        if slot_id not in self._started_order:
            self._started_order.append(slot_id)
        return record
    def stop(self, slot: ISlot, context: SlotContext) -> SlotLifecycleRecord:
        slot_id = slot.manifest().id
        if self.record_for(slot_id).state is not SlotLifecycleState.STARTED:
            return self.record_for(slot_id)
        try:
            slot.stop(context)
        except Exception as exc:  # lifecycle errors must surface as slot errors
            record = SlotLifecycleRecord(
                slot_id=slot_id,
                state=SlotLifecycleState.ERROR,
                error=str(exc),
            )
            self._records[slot_id] = record
            raise SlotConfigurationError(f"slot {slot_id} failed to stop: {exc}") from exc
        record = SlotLifecycleRecord(slot_id=slot_id, state=SlotLifecycleState.STOPPED)
        self._records[slot_id] = record
        if slot_id in self._started_order:
            self._started_order.remove(slot_id)
        return record

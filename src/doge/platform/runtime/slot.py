"""Built-in runtime watcher slot."""

from __future__ import annotations

from doge.core.domain.agent_models import AgentEvent
from doge.platform.slots import (
    SCHEMA_VERSION,
    ISlot,
    SlotCompatibility,
    SlotContribution,
    SlotContext,
    SlotHealth,
    SlotManifest,
    SlotPermissions,
    SlotProvides,
    SlotType,
    WatcherContribution,
    WatcherDecision,
)

_MANIFEST = SlotManifest(
    schema_version=SCHEMA_VERSION,
    id="watcher.runtime_events",
    name="Runtime Event Watcher",
    version="1.0.0",
    type=SlotType.WATCHER,
    owner="agent-runtime",
    maturity="experimental",
    description=(
        "Contributes the default allow-only runtime event watcher used by "
        "slot-aware TransitionRecorder middleware assembly."
    ),
    entrypoint="doge.platform.runtime.slot.RuntimeEventWatcherSlot",
    provides=SlotProvides(
        capabilities=("runtime_event.observe",),
        metadata={"event_types": ("*",), "default_action": "allow"},
    ),
    permissions=SlotPermissions(risk_level="low"),
    health=SlotHealth(status="experimental"),
    feature_flags=("slot_platform", "slot_watcher"),
    compatibility=SlotCompatibility(runtime_min="1"),
)


class RuntimeEventWatcherSlot(ISlot):
    """Built-in watcher slot that preserves current event behavior."""

    def manifest(self) -> SlotManifest:
        return _MANIFEST

    def resolve(self, context: SlotContext) -> SlotContribution:
        return SlotContribution(
            slot_id="watcher.runtime_events",
            watchers=(
                WatcherContribution(
                    watcher_id="watcher.runtime_events.allow_all",
                    on_event=_allow_event,
                ),
            ),
        )


def _allow_event(event: AgentEvent, context: SlotContext) -> WatcherDecision:
    return WatcherDecision(action="allow")

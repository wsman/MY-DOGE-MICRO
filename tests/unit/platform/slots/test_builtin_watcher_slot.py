"""Built-in watcher slot tests for Sprint 038."""

from __future__ import annotations

import pytest

from doge.core.domain.agent_models import AgentEvent, EventType
from doge.platform.runtime.slot import RuntimeEventWatcherSlot
from doge.platform.runtime.watchers import RuntimeEventWatcherMiddleware, WatcherDecisionError
from doge.platform.slots import SlotContext, SlotConfigurationError, SlotType, WatcherContribution, WatcherDecision


def test_runtime_event_watcher_slot_manifest() -> None:
    manifest = RuntimeEventWatcherSlot().manifest()

    assert manifest.id == "watcher.runtime_events"
    assert manifest.type is SlotType.WATCHER
    assert manifest.owner == "agent-runtime"
    assert manifest.feature_flags == ("slot_platform", "slot_watcher")
    assert manifest.provides.capabilities == ("runtime_event.observe",)
    assert manifest.permissions.risk_level == "low"


def test_runtime_event_watcher_slot_contributes_allow_watcher() -> None:
    context = SlotContext(
        settings=object(),
        feature_flags={"slot_platform": True, "slot_watcher": True},
    )
    event = AgentEvent(
        event_id="evt-1",
        run_id="run-1",
        event_type=EventType.RUN_CREATED,
    )

    contribution = RuntimeEventWatcherSlot().resolve(context)

    assert contribution.slot_id == "watcher.runtime_events"
    assert len(contribution.watchers) == 1
    watcher = contribution.watchers[0]
    assert watcher.watcher_id == "watcher.runtime_events.allow_all"
    assert watcher.on_event(event, context).action == "allow"


def test_runtime_event_watcher_middleware_blocks_blocking_decision() -> None:
    context = SlotContext(
        settings=object(),
        feature_flags={"slot_platform": True, "slot_watcher": True},
    )
    middleware = RuntimeEventWatcherMiddleware(
        (
            WatcherContribution(
                "watcher.block",
                lambda _event, _context: WatcherDecision(
                    action="block",
                    reason="blocked by test",
                    approval_required=True,
                ),
            ),
        ),
        context,
    )
    event = AgentEvent(
        event_id="evt-1",
        run_id="run-1",
        event_type=EventType.TOOL_CALL,
    )

    with pytest.raises(WatcherDecisionError, match="blocked by test") as exc:
        middleware.enforce(event)

    assert exc.value.watcher_id == "watcher.block"
    assert exc.value.action == "block"
    assert exc.value.approval_required is True


def test_runtime_event_watcher_middleware_rejects_unknown_action() -> None:
    context = SlotContext(
        settings=object(),
        feature_flags={"slot_platform": True, "slot_watcher": True},
    )
    middleware = RuntimeEventWatcherMiddleware(
        (
            WatcherContribution(
                "watcher.bad",
                lambda _event, _context: WatcherDecision(action="unsupported"),
            ),
        ),
        context,
    )
    event = AgentEvent(
        event_id="evt-1",
        run_id="run-1",
        event_type=EventType.TOOL_CALL,
    )

    with pytest.raises(SlotConfigurationError, match="unsupported action"):
        middleware.enforce(event)

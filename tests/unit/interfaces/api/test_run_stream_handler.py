"""Unit tests for RunStreamHandler streaming semantics.

These tests verify the canonical live-SSE contract per ADR-0025:
- Replays historical events via ``runtime.list_events``
- Subscribes to live events via ``IEventSubscriber.subscribe``
- Closes on terminal status or terminal event
- Does NOT use ``runtime.stream_events`` (replay-only)
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from doge.core.domain.agent_models import AgentEvent, EventType, RunStatus
from doge.interfaces.api.handlers import RunAccessContext
from doge.interfaces.api.handlers.streaming import RunStreamHandler
from doge.shared.scope import TenantScope


def _make_event(sequence: int, event_type: str = "model_response") -> AgentEvent:
    return AgentEvent(
        event_id=f"evt-{sequence}",
        run_id="run-1",
        event_type=EventType(event_type),
        payload={},
        sequence=sequence,
        schema_version="1.0",
    )


class FakeRuntime:
    def __init__(self, events: list[AgentEvent], status: RunStatus = RunStatus.RUNNING) -> None:
        self._events = events
        self._status = status
        self.list_events_calls: list[tuple[Any, str]] = []
        self.get_run_calls: list[tuple[Any, str]] = []

    def list_events(self, scope, run_id: str) -> list[AgentEvent]:
        self.list_events_calls.append((scope, run_id))
        return list(self._events)

    def get_run(self, scope, run_id: str):
        self.get_run_calls.append((scope, run_id))
        return SimpleNamespace(
            run_id=run_id,
            status=self._status,
            identity_snapshot=None,
        )


class FakeSubscriber:
    def __init__(self, events: list[AgentEvent]) -> None:
        self._events = events
        self.subscribe_calls: list[tuple[str, int]] = []

    async def subscribe(self, run_id: str, after_sequence: int = 0):
        self.subscribe_calls.append((run_id, after_sequence))
        for event in self._events:
            if event.sequence > after_sequence:
                yield event


@pytest.mark.asyncio
async def test_run_stream_handler_replays_then_subscribes() -> None:
    """Handler should yield historical events then switch to live subscriber events."""
    replay_events = [_make_event(1, "run_created"), _make_event(2)]
    live_events = [_make_event(3, "tool_call"), _make_event(4, "artifact_created")]
    runtime = FakeRuntime(replay_events, status=RunStatus.RUNNING)
    subscriber = FakeSubscriber(replay_events + live_events)
    access = RunAccessContext(scope=TenantScope.local())

    handler = RunStreamHandler(runtime=runtime, subscriber=subscriber)
    stream = handler.open(run_id="run-1", access=access, after_sequence=0)

    received = [event async for event in stream]

    assert [e.sequence for e in received] == [1, 2, 3, 4]
    assert runtime.list_events_calls == [(access.scope, "run-1")]
    assert subscriber.subscribe_calls == [("run-1", 0)]


@pytest.mark.asyncio
async def test_run_stream_handler_subscribes_after_sequence() -> None:
    """The handler asks the subscriber for events after the requested sequence."""
    replay_events = [_make_event(1), _make_event(2)]
    live_events = [_make_event(3)]
    runtime = FakeRuntime(replay_events, status=RunStatus.RUNNING)
    subscriber = FakeSubscriber(replay_events + live_events)
    access = RunAccessContext(scope=TenantScope.local())

    handler = RunStreamHandler(runtime=runtime, subscriber=subscriber)
    stream = handler.open(run_id="run-1", access=access, after_sequence=0)

    received = [event async for event in stream]

    assert [e.sequence for e in received] == [1, 2, 3]
    assert runtime.list_events_calls == [(access.scope, "run-1")]
    assert subscriber.subscribe_calls == [("run-1", 0)]


@pytest.mark.asyncio
async def test_run_stream_handler_resumes_after_last_event_id() -> None:
    """When Last-Event-ID is provided, the subscriber resumes from that point."""
    replay_events = [_make_event(1), _make_event(2)]
    live_events = [_make_event(3)]
    runtime = FakeRuntime(replay_events, status=RunStatus.RUNNING)
    subscriber = FakeSubscriber(replay_events + live_events)
    access = RunAccessContext(scope=TenantScope.local())

    handler = RunStreamHandler(runtime=runtime, subscriber=subscriber)
    stream = handler.open(run_id="run-1", access=access, after_sequence=2)

    received = [event async for event in stream]

    assert [e.sequence for e in received] == [3]
    assert subscriber.subscribe_calls == [("run-1", 2)]


@pytest.mark.asyncio
async def test_run_stream_handler_closes_on_terminal_status() -> None:
    """When the run is already terminal, close after reaching the max persisted sequence."""
    replay_events = [_make_event(1)]
    runtime = FakeRuntime(replay_events, status=RunStatus.COMPLETED)
    subscriber = FakeSubscriber(replay_events)
    access = RunAccessContext(scope=TenantScope.local())

    handler = RunStreamHandler(runtime=runtime, subscriber=subscriber)
    stream = handler.open(run_id="run-1", access=access, after_sequence=0)

    received = [event async for event in stream]

    assert [e.sequence for e in received] == [1]


@pytest.mark.asyncio
async def test_run_stream_handler_closes_on_terminal_event() -> None:
    """When a terminal event arrives, the handler closes even if status is RUNNING."""
    replay_events = [_make_event(1)]
    live_events = [_make_event(2, "model_response"), _make_event(3, "artifact_created")]
    runtime = FakeRuntime(replay_events, status=RunStatus.RUNNING)
    subscriber = FakeSubscriber(replay_events + live_events)
    access = RunAccessContext(scope=TenantScope.local())

    handler = RunStreamHandler(runtime=runtime, subscriber=subscriber)
    stream = handler.open(run_id="run-1", access=access, after_sequence=0)

    received = [event async for event in stream]

    assert [e.sequence for e in received] == [1, 2, 3]


@pytest.mark.asyncio
async def test_run_stream_handler_uses_list_events_not_stream_events() -> None:
    """Handler must use ``runtime.list_events`` for replay, not ``stream_events``.

    This is the core ADR-0025 contract: ``stream_events`` is replay-only and
    must not be used by the canonical live SSE handler.
    """
    replay_events = [_make_event(1)]
    runtime = FakeRuntime(replay_events, status=RunStatus.COMPLETED)
    subscriber = FakeSubscriber(replay_events)
    access = RunAccessContext(scope=TenantScope.local())

    handler = RunStreamHandler(runtime=runtime, subscriber=subscriber)
    stream = handler.open(run_id="run-1", access=access, after_sequence=0)

    async for _ in stream:
        pass

    assert runtime.list_events_calls
    assert not hasattr(runtime, "stream_events_calls")


@pytest.mark.asyncio
async def test_run_stream_handler_empty_historical_live_only() -> None:
    """Handler should work correctly when there are no historical events to replay."""
    live_events = [_make_event(1), _make_event(2, "artifact_created")]
    runtime = FakeRuntime([], status=RunStatus.RUNNING)
    subscriber = FakeSubscriber(live_events)
    access = RunAccessContext(scope=TenantScope.local())

    handler = RunStreamHandler(runtime=runtime, subscriber=subscriber)
    stream = handler.open(run_id="run-1", access=access, after_sequence=0)

    received = [event async for event in stream]

    assert [e.sequence for e in received] == [1, 2]


@pytest.mark.asyncio
async def test_run_stream_handler_no_events_at_all() -> None:
    """Handler should yield nothing when there are no historical or live events."""
    runtime = FakeRuntime([], status=RunStatus.RUNNING)
    subscriber = FakeSubscriber([])
    access = RunAccessContext(scope=TenantScope.local())

    handler = RunStreamHandler(runtime=runtime, subscriber=subscriber)
    stream = handler.open(run_id="run-1", access=access, after_sequence=0)

    received = [event async for event in stream]

    assert received == []

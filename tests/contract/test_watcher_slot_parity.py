"""Watcher slot consumer parity and enforcement tests (Sprint 038)."""

from __future__ import annotations

import pytest

from doge.application.agent.transition_recorder import TransitionRecorder
from doge.bootstrap.runtime_factories import slots as slots_module
from doge.config import reset_settings
from doge.core.domain.agent_models import AgentEvent, AgentRun, EventType
from doge.core.ports.event_publisher import IEventPublisher
from doge.core.ports.runtime_transaction import IRuntimeTransaction, IRuntimeTransactionFactory
from doge.platform.runtime.watchers import RuntimeEventWatcherMiddleware, WatcherDecisionError
from doge.platform.slots import (
    ISlot,
    SlotConfigurationError,
    SlotContribution,
    SlotContext,
    SlotHealth,
    SlotManifest,
    SlotProvides,
    SlotRegistry,
    SlotType,
    WatcherContribution,
    WatcherDecision,
)

_ALL_FEATURE_VARS = [
    "DOGE_FEATURE_RUN_SUMMARY_API",
    "DOGE_FEATURE_PLATFORM_OBJECTS",
    "DOGE_FEATURE_WORKFLOW_TEMPLATES",
    "DOGE_FEATURE_CAPABILITY_REGISTRY",
    "DOGE_FEATURE_RUNTIME_OUTBOX_PUBLISHER",
    "DOGE_FEATURE_PYTHON_ANALYSIS_ENABLED",
    "DOGE_FEATURE_SLOT_PLATFORM",
    "DOGE_FEATURE_SLOT_GOVERNANCE",
    "DOGE_FEATURE_SLOT_WATCHER",
    "DOGE_FEATURE_SLOT_UI",
    "DOGE_FEATURE_SLOT_ENFORCEMENT",
    "DOGE_FEATURE_SLOT_LOADER",
    "DOGE_FEATURE_SLOT_INSTALL",
]


class _FakeTransaction(IRuntimeTransaction):
    def __init__(self) -> None:
        self.saved_runs = []
        self.appended_events = []
        self.saved_artifacts = []
        self.saved_approvals = []
        self.staged_outbox = []
        self.committed = False
        self.rolled_back = False

    def save_run(self, run: AgentRun) -> None:
        self.saved_runs.append(run)

    def append_event(self, event: AgentEvent) -> AgentEvent:
        self.appended_events.append(event)
        return event

    def save_artifact(self, artifact) -> None:
        self.saved_artifacts.append(artifact)

    def save_approval(self, approval) -> None:
        self.saved_approvals.append(approval)

    def stage_outbox(self, event: AgentEvent) -> None:
        self.staged_outbox.append(event)

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True


class _FakeTransactionFactory(IRuntimeTransactionFactory):
    def __init__(self, tx: _FakeTransaction) -> None:
        self._tx = tx

    def begin(self) -> _FakeTransaction:
        return self._tx


class _CapturingPublisher(IEventPublisher):
    def __init__(self) -> None:
        self.events: list[AgentEvent] = []

    async def publish(self, event: AgentEvent) -> None:
        self.events.append(event)


class _WatcherSlot(ISlot):
    def __init__(
        self,
        slot_id: str,
        *,
        watcher_id: str,
        decision: WatcherDecision,
        event_types: tuple[str, ...] = (),
    ) -> None:
        self._slot_id = slot_id
        self._watcher_id = watcher_id
        self._decision = decision
        self._event_types = event_types

    def manifest(self) -> SlotManifest:
        return SlotManifest(
            schema_version=1,
            id=self._slot_id,
            name="Test Watcher Slot",
            version="1.0.0",
            type=SlotType.WATCHER,
            owner="slot-tests",
            maturity="experimental",
            description="Test watcher slot.",
            entrypoint="tests.contract.test_watcher_slot_parity.WatcherSlot",
            provides=SlotProvides(capabilities=("runtime_event.observe",)),
            health=SlotHealth(status="experimental"),
            feature_flags=("slot_platform", "slot_watcher"),
        )

    def resolve(self, context: SlotContext) -> SlotContribution:
        return SlotContribution(
            slot_id=self._slot_id,
            watchers=(
                WatcherContribution(
                    self._watcher_id,
                    lambda _event, _context: self._decision,
                    event_types=self._event_types,
                ),
            ),
        )


def _strip_feature_env(monkeypatch, keep: set[str] | None = None) -> None:
    keep = keep or set()
    for var in _ALL_FEATURE_VARS:
        if var not in keep:
            monkeypatch.delenv(var, raising=False)


def test_watcher_slot_off_returns_no_runtime_middleware(monkeypatch) -> None:
    _strip_feature_env(monkeypatch, keep={"DOGE_FEATURE_SLOT_PLATFORM"})
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    reset_settings()

    assert slots_module.build_slot_aware_runtime_event_watcher() is None


@pytest.mark.asyncio
async def test_default_watcher_slot_preserves_transition_recorder_behavior(monkeypatch) -> None:
    _strip_feature_env(
        monkeypatch,
        keep={"DOGE_FEATURE_SLOT_PLATFORM", "DOGE_FEATURE_SLOT_WATCHER"},
    )
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    monkeypatch.setenv("DOGE_FEATURE_SLOT_WATCHER", "1")
    reset_settings()
    tx = _FakeTransaction()
    publisher = _CapturingPublisher()
    middleware = slots_module.build_slot_aware_runtime_event_watcher()
    run = AgentRun.create(workflow="test", question="Q")
    recorder = TransitionRecorder(
        transaction_factory=_FakeTransactionFactory(tx),
        event_publisher=publisher,
        event_watcher=middleware,
    )

    events = await recorder.record(run, events=[(EventType.RUN_CREATED, {})])

    assert isinstance(middleware, RuntimeEventWatcherMiddleware)
    assert len(events) == 1
    assert tx.appended_events == events
    assert tx.staged_outbox == events
    assert tx.committed is True
    assert tx.rolled_back is False
    assert publisher.events == events


@pytest.mark.asyncio
async def test_custom_watcher_blocks_event_before_outbox_and_publish(monkeypatch) -> None:
    registry = SlotRegistry()
    registry.register(
        _WatcherSlot(
            "watcher.blocker",
            watcher_id="watcher.blocker",
            decision=WatcherDecision(action="block", reason="blocked by policy"),
            event_types=(EventType.TOOL_CALL.value,),
        )
    )
    monkeypatch.setattr(slots_module, "build_builtin_slot_registry", lambda: registry)
    _strip_feature_env(
        monkeypatch,
        keep={"DOGE_FEATURE_SLOT_PLATFORM", "DOGE_FEATURE_SLOT_WATCHER"},
    )
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    monkeypatch.setenv("DOGE_FEATURE_SLOT_WATCHER", "1")
    reset_settings()
    tx = _FakeTransaction()
    publisher = _CapturingPublisher()
    middleware = slots_module.build_slot_aware_runtime_event_watcher()
    run = AgentRun.create(workflow="test", question="Q")
    recorder = TransitionRecorder(
        transaction_factory=_FakeTransactionFactory(tx),
        event_publisher=publisher,
        event_watcher=middleware,
    )

    with pytest.raises(WatcherDecisionError, match="blocked by policy"):
        await recorder.record(run, events=[(EventType.TOOL_CALL, {"tool": "publish"})])

    assert len(tx.appended_events) == 1
    assert tx.staged_outbox == []
    assert tx.committed is False
    assert tx.rolled_back is True
    assert publisher.events == []


def test_duplicate_watcher_contribution_fails_fast(monkeypatch) -> None:
    registry = SlotRegistry()
    registry.register(
        _WatcherSlot(
            "watcher.one",
            watcher_id="watcher.duplicate",
            decision=WatcherDecision(action="allow"),
        )
    )
    registry.register(
        _WatcherSlot(
            "watcher.two",
            watcher_id="watcher.duplicate",
            decision=WatcherDecision(action="allow"),
        )
    )
    monkeypatch.setattr(slots_module, "build_builtin_slot_registry", lambda: registry)
    _strip_feature_env(
        monkeypatch,
        keep={"DOGE_FEATURE_SLOT_PLATFORM", "DOGE_FEATURE_SLOT_WATCHER"},
    )
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    monkeypatch.setenv("DOGE_FEATURE_SLOT_WATCHER", "1")
    reset_settings()

    with pytest.raises(SlotConfigurationError, match="duplicate watcher"):
        slots_module.build_slot_aware_runtime_event_watcher()

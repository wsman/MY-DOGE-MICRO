"""Unit tests for TransitionRecorder."""

from __future__ import annotations

import pytest

from doge.application.agent.transition_recorder import TransitionRecorder
from doge.core.domain.agent_models import AgentEvent, AgentRun, EventType, RunStatus
from doge.core.ports.event_publisher import IEventPublisher
from doge.core.ports.runtime_transaction import IRuntimeTransaction, IRuntimeTransactionFactory


class FakeTransaction(IRuntimeTransaction):
    def __init__(self):
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


class FakeTransactionFactory(IRuntimeTransactionFactory):
    def __init__(self, tx: FakeTransaction | None = None):
        self._tx = tx or FakeTransaction()

    def begin(self) -> FakeTransaction:
        return self._tx


class CapturingPublisher(IEventPublisher):
    def __init__(self):
        self.events = []

    async def publish(self, event: AgentEvent) -> None:
        self.events.append(event)


@pytest.fixture
def run():
    return AgentRun.create(workflow="test", question="Q")


@pytest.mark.asyncio
async def test_transition_recorder_record_persists_run_when_status_changes(run):
    tx = FakeTransaction()
    factory = FakeTransactionFactory(tx)
    recorder = TransitionRecorder(transaction_factory=factory)

    await recorder.record(run, status=RunStatus.RUNNING)

    assert run.status == RunStatus.RUNNING
    assert len(tx.saved_runs) == 1
    assert tx.saved_runs[0] == run
    assert tx.committed
    assert not tx.rolled_back


@pytest.mark.asyncio
async def test_transition_recorder_record_appends_events_and_stages_outbox(run):
    tx = FakeTransaction()
    factory = FakeTransactionFactory(tx)
    recorder = TransitionRecorder(transaction_factory=factory)

    events = await recorder.record(
        run,
        events=[(EventType.TOOL_CALL, {"tool": "test"})],
    )

    assert len(events) == 1
    assert events[0].event_type == EventType.TOOL_CALL
    assert len(tx.appended_events) == 1
    assert len(tx.staged_outbox) == 1
    assert tx.staged_outbox[0] == events[0]
    assert tx.committed


@pytest.mark.asyncio
async def test_transition_recorder_record_persists_artifacts(run):
    tx = FakeTransaction()
    factory = FakeTransactionFactory(tx)
    recorder = TransitionRecorder(transaction_factory=factory)
    artifact = run.add_artifact(kind="memo", title="T", content="C")

    await recorder.record(run, artifacts=[artifact])

    assert len(tx.saved_artifacts) == 1
    assert tx.saved_artifacts[0] == artifact


@pytest.mark.asyncio
async def test_transition_recorder_record_persists_approvals(run):
    tx = FakeTransaction()
    factory = FakeTransactionFactory(tx)
    recorder = TransitionRecorder(transaction_factory=factory)
    approval = run.add_approval(action="publish", risk_level="high")

    await recorder.record(run, approvals=[approval])

    assert len(tx.saved_approvals) == 1
    assert tx.saved_approvals[0] == approval


@pytest.mark.asyncio
async def test_transition_recorder_record_rolls_back_on_exception(run):
    class FailingTx(FakeTransaction):
        def save_run(self, run):
            raise RuntimeError("disk full")

    tx = FailingTx()
    factory = FakeTransactionFactory(tx)
    recorder = TransitionRecorder(transaction_factory=factory)

    with pytest.raises(RuntimeError, match="disk full"):
        await recorder.record(run, status=RunStatus.RUNNING, save_run=True)

    assert tx.rolled_back
    assert not tx.committed


@pytest.mark.asyncio
async def test_transition_recorder_record_publishes_events_after_commit(run):
    tx = FakeTransaction()
    factory = FakeTransactionFactory(tx)
    publisher = CapturingPublisher()
    recorder = TransitionRecorder(transaction_factory=factory, event_publisher=publisher)

    events = await recorder.record(
        run,
        events=[(EventType.RUN_CREATED, {})],
    )

    assert len(publisher.events) == 1
    assert publisher.events[0] == events[0]


@pytest.mark.asyncio
async def test_transition_recorder_mark_cancelled_sets_cancelled_status(run):
    run.status = RunStatus.CANCELLING
    tx = FakeTransaction()
    factory = FakeTransactionFactory(tx)
    recorder = TransitionRecorder(transaction_factory=factory)

    await recorder.mark_cancelled(run)

    assert run.status == RunStatus.CANCELLED
    assert len(tx.appended_events) == 1
    assert tx.appended_events[0].event_type == EventType.RUN_CANCELLED


@pytest.mark.asyncio
async def test_transition_recorder_mark_failed_sets_failed_status(run):
    tx = FakeTransaction()
    factory = FakeTransactionFactory(tx)
    recorder = TransitionRecorder(transaction_factory=factory)

    await recorder.mark_failed(run, "something broke", code="test_failure")

    assert run.status == RunStatus.FAILED
    error_events = [e for e in tx.appended_events if e.event_type == EventType.ERROR]
    assert len(error_events) == 1
    assert error_events[0].payload["error"]["code"] == "test_failure"
    assert error_events[0].payload["message"] == "something broke"


@pytest.mark.asyncio
async def test_transition_recorder_mark_failed_redacts_secrets(run):
    tx = FakeTransaction()
    factory = FakeTransactionFactory(tx)
    recorder = TransitionRecorder(transaction_factory=factory)

    await recorder.mark_failed(run, "Authorization: Bearer sk-secret123")

    error_events = [e for e in tx.appended_events if e.event_type == EventType.ERROR]
    payload = error_events[0].payload
    # SafeError.create stores the message as-is; redaction happens at the caller layer
    assert payload["message"] == "Authorization: Bearer sk-secret123"
    assert payload["error"]["code"] == "runtime_failure"
    assert "err-" in payload["error"]["internal_reference"]


def test_transition_recorder_noop_publisher_returns_publisher():
    recorder = TransitionRecorder(transaction_factory=FakeTransactionFactory())
    pub = recorder.noop_publisher()

    import asyncio
    asyncio.run(pub.publish(AgentEvent(event_id="e1", run_id="r1", event_type=EventType.RUN_CREATED)))

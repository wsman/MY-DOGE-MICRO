"""Unit tests for ApprovalCoordinator."""

from __future__ import annotations

import pytest

from doge.application.agent.approval_coordinator import ApprovalCoordinator
from doge.application.agent.transition_recorder import TransitionRecorder
from doge.core.domain.agent_models import AgentApproval, AgentEvent, AgentRun, EventType, RunStatus
from doge.core.ports.agent_repository import IApprovalRepository, IRunRepository
from doge.shared.scope import TenantScope


class FakeRunRepository(IRunRepository):
    def __init__(self):
        self.runs = {}

    def save(self, run, scope=None):
        pass

    def get(self, run_id, *, tenant_id=None):
        return self.runs.get(run_id)

    def get_run_header(self, run_id, *, tenant_id=None):
        return self.runs.get(run_id)

    def list_by_session(self, session_id, scope=None, limit=20):
        return []

    def list_recent(self, scope=None, limit=20):
        return []


class FakeApprovalRepository(IApprovalRepository):
    def __init__(self):
        self.approvals = {}

    def save(self, approval, scope=None):
        pass

    def get(self, approval_id, *, tenant_id=None):
        return self.approvals.get(approval_id)

    def list_for_run(self, run_id, *, tenant_id=None):
        return [a for a in self.approvals.values() if a.run_id == run_id]


class FakeTx:
    def __init__(self):
        self.saved_runs = []
        self.appended_events = []
        self.saved_approvals = []
        self.staged_outbox = []
        self.committed = False
        self.rolled_back = False

    def save_run(self, run):
        self.saved_runs.append(run)

    def append_event(self, event):
        self.appended_events.append(event)
        return event

    def save_artifact(self, artifact):
        pass

    def save_approval(self, approval):
        self.saved_approvals.append(approval)

    def stage_outbox(self, event):
        self.staged_outbox.append(event)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


class FakeTxFactory:
    def __init__(self, tx=None):
        self._tx = tx or FakeTx()

    def begin(self):
        return self._tx


@pytest.fixture
def run():
    r = AgentRun.create(workflow="test", question="Q")
    r.status = RunStatus.AWAITING_APPROVAL
    return r


@pytest.fixture
def approval(run):
    a = AgentApproval(
        approval_id="appr-1",
        action="publish",
        risk_level="high",
        run_id=run.run_id,
        why_needed="Publishing requires review.",
        impact="Memo can be distributed.",
        deny_consequence="Run stops before publishing.",
        publish_target="ic@example.com",
    )
    return a


@pytest.fixture
def run_repository(run):
    repo = FakeRunRepository()
    repo.runs[run.run_id] = run
    return repo


@pytest.fixture
def approval_repository(approval):
    repo = FakeApprovalRepository()
    repo.approvals[approval.approval_id] = approval
    return repo


@pytest.fixture
def transition_recorder():
    return TransitionRecorder(transaction_factory=FakeTxFactory())


@pytest.fixture
def coordinator(run_repository, approval_repository, transition_recorder):
    return ApprovalCoordinator(
        run_repository=run_repository,
        approval_repository=approval_repository,
        transition_recorder=transition_recorder,
    )


@pytest.mark.asyncio
async def test_approval_coordinator_resolve_approved_queues_run(coordinator, run, approval):
    result = await coordinator.resolve(
        TenantScope.local(), run.run_id, approval.approval_id, True
    )

    assert result.status == RunStatus.QUEUED
    assert approval.status == "approved"
    assert approval.resolved_at is not None
    assert approval.why_needed == "Publishing requires review."
    assert approval.impact == "Memo can be distributed."
    assert approval.deny_consequence == "Run stops before publishing."
    assert approval.publish_target == "ic@example.com"


@pytest.mark.asyncio
async def test_approval_coordinator_resolve_denied_fails_run(coordinator, run, approval):
    result = await coordinator.resolve(
        TenantScope.local(), run.run_id, approval.approval_id, False
    )

    assert result.status == RunStatus.FAILED
    assert approval.status == "denied"


@pytest.mark.asyncio
async def test_approval_coordinator_resolve_records_approval_resolved_event(coordinator, run, approval):
    await coordinator.resolve(TenantScope.local(), run.run_id, approval.approval_id, True)

    assert any(
        e.event_type == EventType.APPROVAL_RESOLVED
        and e.payload.get("approved") is True
        for e in run.events
    )


@pytest.mark.asyncio
async def test_approval_coordinator_resolve_records_run_queued_event_on_approval(coordinator, run, approval):
    await coordinator.resolve(TenantScope.local(), run.run_id, approval.approval_id, True)

    assert any(e.event_type == EventType.RUN_QUEUED for e in run.events)


@pytest.mark.asyncio
async def test_approval_coordinator_resolve_does_not_queue_on_denial(coordinator, run, approval):
    await coordinator.resolve(TenantScope.local(), run.run_id, approval.approval_id, False)

    assert not any(e.event_type == EventType.RUN_QUEUED for e in run.events)


@pytest.mark.asyncio
async def test_approval_coordinator_resolve_raises_when_approval_not_found(coordinator, run):
    with pytest.raises(KeyError, match="approval not found"):
        await coordinator.resolve(TenantScope.local(), run.run_id, "nonexistent", True)


@pytest.mark.asyncio
async def test_approval_coordinator_resolve_raises_when_approval_belongs_to_different_run(
    coordinator, run, approval_repository
):
    other_approval = AgentApproval(approval_id="appr-2", action="x", risk_level="low", run_id="other-run")
    approval_repository.approvals[other_approval.approval_id] = other_approval

    with pytest.raises(KeyError, match="approval not found"):
        await coordinator.resolve(TenantScope.local(), run.run_id, other_approval.approval_id, True)


@pytest.mark.asyncio
async def test_approval_coordinator_resolve_raises_when_run_not_found(coordinator):
    with pytest.raises(KeyError, match="run not found"):
        await coordinator.resolve(TenantScope.local(), "nonexistent", "appr-1", True)

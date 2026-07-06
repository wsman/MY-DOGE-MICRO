"""Unit tests for RunLifecycleService."""

from __future__ import annotations

import pytest

from doge.application.agent.approval_coordinator import ApprovalCoordinator
from doge.application.agent.artifact_finalizer import ArtifactFinalizer
from doge.application.agent.context_builder import ContextBuilder
from doge.application.agent.model_response_assembler import ModelResponseAssembler
from doge.application.agent.run_lifecycle_service import RunLifecycleService
from doge.application.agent.run_stepper import RunStepper
from doge.application.agent.transition_recorder import TransitionRecorder
from doge.core.domain.agent_models import AgentEvent, AgentRun, EventType, RunStatus
from doge.core.domain.model_policy import ModelPolicy
from doge.core.ports.agent_model import AgentMessage, AgentResponse
from doge.core.ports.agent_repository import (
    IApprovalRepository,
    IArtifactRepository,
    IEventRepository,
    IRunRepository,
)
from doge.core.ports.runtime_services import IModelExecutionService, IToolExecutionService, ModelExecutionResult, ToolResult
from doge.shared.scope import TenantScope


class FakeRunRepository(IRunRepository):
    def __init__(self):
        self.runs = {}
        self._session_runs = {}

    def save(self, run, scope=None):
        self.runs[run.run_id] = run

    def get(self, run_id, *, tenant_id=None):
        return self.runs.get(run_id)

    def get_run_header(self, run_id, *, tenant_id=None):
        return self.runs.get(run_id)

    def list_by_session(self, session_id, limit=20, *, tenant_id=None):
        return self._session_runs.get(session_id, [])[:limit]

    def list_recent(self, limit=20, *, tenant_id=None):
        return list(self.runs.values())[:limit]


class FakeEventRepository(IEventRepository):
    def __init__(self):
        self.events = []

    def append(self, event, scope=None):
        self.events.append(event)
        return event

    def list_for_run(self, run_id, *, tenant_id=None, after_sequence=0):
        return [e for e in self.events if e.run_id == run_id]


class FakeArtifactRepository(IArtifactRepository):
    def __init__(self):
        self.artifacts = []

    def save(self, artifact, scope=None):
        self.artifacts.append(artifact)

    def list_for_run(self, run_id, *, tenant_id=None):
        return [a for a in self.artifacts if a.run_id == run_id]


class FakeApprovalRepository(IApprovalRepository):
    def __init__(self):
        self.approvals = []

    def save(self, approval, scope=None):
        self.approvals.append(approval)

    def get(self, approval_id, *, tenant_id=None):
        for a in self.approvals:
            if a.approval_id == approval_id:
                return a
        return None

    def list_for_run(self, run_id, *, tenant_id=None):
        return [a for a in self.approvals if a.run_id == run_id]


class ConnectedFakeTx:
    def __init__(self, event_repo=None, artifact_repo=None, approval_repo=None, run_repo=None):
        self.saved_runs = []
        self.appended_events = []
        self.saved_artifacts = []
        self.saved_approvals = []
        self.staged_outbox = []
        self.committed = False
        self.rolled_back = False
        self._event_repo = event_repo
        self._artifact_repo = artifact_repo
        self._approval_repo = approval_repo
        self._run_repo = run_repo

    def save_run(self, run):
        self.saved_runs.append(run)
        if self._run_repo is not None:
            self._run_repo.save(run, None)

    def append_event(self, event):
        self.appended_events.append(event)
        if self._event_repo is not None:
            self._event_repo.append(event, None)
        return event

    def save_artifact(self, artifact):
        self.saved_artifacts.append(artifact)
        if self._artifact_repo is not None:
            self._artifact_repo.save(artifact, None)

    def save_approval(self, approval):
        self.saved_approvals.append(approval)
        if self._approval_repo is not None:
            self._approval_repo.save(approval, None)

    def stage_outbox(self, event):
        self.staged_outbox.append(event)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


class ConnectedFakeTxFactory:
    def __init__(self, event_repo=None, artifact_repo=None, approval_repo=None, run_repo=None):
        self.event_repo = event_repo
        self.artifact_repo = artifact_repo
        self.approval_repo = approval_repo
        self.run_repo = run_repo

    def begin(self):
        return ConnectedFakeTx(
            event_repo=self.event_repo,
            artifact_repo=self.artifact_repo,
            approval_repo=self.approval_repo,
            run_repo=self.run_repo,
        )


class FakeModelExecutionService(IModelExecutionService):
    def __init__(self, response_content="final memo"):
        self.response_content = response_content

    async def execute(self, *, run, policy, messages, tool_schemas_for, enterprise_context=None, execution_context=None):
        return ModelExecutionResult(
            response=AgentResponse(
                message=AgentMessage(role="assistant", content=self.response_content)
            ),
            routing=None,
            routing_payload={},
        )


class FakeToolExecutionService(IToolExecutionService):
    def schemas_for(self, routing, context=None):
        return []

    async def execute(self, *, context, tool_name, arguments, run_id, timeout_seconds, request_id):
        return ToolResult(name=tool_name, data={"result": "ok"})

    def audit(self, context, event_type, resource_type, resource_id, metadata=None, *, request_id=None):
        pass


class FakeArtifactEvaluationService:
    def artifact_content(self, content):
        return content or ""

    def metrics(self, artifact_text, events):
        return {}


class FakeContextBuilder:
    def build(self, run, events, *, enterprise_context=None, execution_context=None):
        return []


class OneStepRunStepper(RunStepper):
    """A stepper that completes in one step."""

    def __init__(self, run_repository, transition_recorder):
        self._runs = run_repository
        self._recorder = transition_recorder

    async def step(self, scope, run_id):
        run = self._runs.get(run_id, tenant_id=scope.tenant_id)
        run.status = RunStatus.COMPLETED
        return run


class ApprovalStepper(RunStepper):
    """A stepper that pauses awaiting approval."""

    def __init__(self, run_repository, transition_recorder):
        self._runs = run_repository
        self._recorder = transition_recorder

    async def step(self, scope, run_id):
        run = self._runs.get(run_id, tenant_id=scope.tenant_id)
        run.status = RunStatus.AWAITING_APPROVAL
        return run


class FailingStepper(RunStepper):
    """A stepper that fails."""

    def __init__(self, run_repository, transition_recorder):
        self._runs = run_repository
        self._recorder = transition_recorder

    async def step(self, scope, run_id):
        run = self._runs.get(run_id, tenant_id=scope.tenant_id)
        run.status = RunStatus.FAILED
        return run


class LoopingStepper(RunStepper):
    """A stepper that keeps running forever."""

    def __init__(self, run_repository, transition_recorder):
        self._runs = run_repository
        self._recorder = transition_recorder

    async def step(self, scope, run_id):
        run = self._runs.get(run_id, tenant_id=scope.tenant_id)
        run.status = RunStatus.RUNNING
        return run


@pytest.fixture
def run_repository():
    return FakeRunRepository()


@pytest.fixture
def event_repository():
    return FakeEventRepository()


@pytest.fixture
def artifact_repository():
    return FakeArtifactRepository()


@pytest.fixture
def approval_repository():
    return FakeApprovalRepository()


@pytest.fixture
def transition_recorder(event_repository, artifact_repository, approval_repository, run_repository):
    return TransitionRecorder(
        transaction_factory=ConnectedFakeTxFactory(
            event_repo=event_repository,
            artifact_repo=artifact_repository,
            approval_repo=approval_repository,
            run_repo=run_repository,
        ),
    )


@pytest.fixture
def lifecycle_service(run_repository, event_repository, artifact_repository, approval_repository, transition_recorder):
    stepper = OneStepRunStepper(run_repository, transition_recorder)
    return RunLifecycleService(
        run_repository=run_repository,
        event_repository=event_repository,
        artifact_repository=artifact_repository,
        approval_repository=approval_repository,
        transition_recorder=transition_recorder,
        run_stepper=stepper,
    )


@pytest.mark.asyncio
async def test_lifecycle_service_create_run_persists_run(lifecycle_service, run_repository):
    run = await lifecycle_service.create_run(TenantScope.local(), {"question": "Analyze AAPL"})

    assert run.run_id in run_repository.runs
    assert run.question == "Analyze AAPL"
    assert run.status == RunStatus.CREATED


@pytest.mark.asyncio
async def test_lifecycle_service_create_run_records_created_event(lifecycle_service, run_repository):
    run = await lifecycle_service.create_run(TenantScope.local(), {"question": "Analyze AAPL"})

    assert any(e.event_type == EventType.RUN_CREATED for e in run.events)


@pytest.mark.asyncio
async def test_lifecycle_service_create_run_with_model_policy(lifecycle_service, run_repository):
    run = await lifecycle_service.create_run(TenantScope.local(), {
        "question": "Analyze AAPL",
        "model_policy": {"max_tool_rounds": 5},
    })

    assert run.model_policy.max_tool_rounds == 5


@pytest.mark.asyncio
async def test_lifecycle_service_run_to_pause_or_completion_completes(run_repository, transition_recorder):
    service = RunLifecycleService(
        run_repository=run_repository,
        event_repository=FakeEventRepository(),
        artifact_repository=FakeArtifactRepository(),
        approval_repository=FakeApprovalRepository(),
        transition_recorder=transition_recorder,
        run_stepper=OneStepRunStepper(run_repository, transition_recorder),
    )
    run = AgentRun.create(workflow="test", question="Q")
    run.status = RunStatus.QUEUED
    run_repository.save(run, TenantScope.local())

    result = await service.run_to_pause_or_completion(TenantScope.local(), run.run_id)

    assert result.status == RunStatus.COMPLETED


@pytest.mark.asyncio
async def test_lifecycle_service_run_to_pause_or_completion_stops_on_approval(run_repository, transition_recorder):
    service = RunLifecycleService(
        run_repository=run_repository,
        event_repository=FakeEventRepository(),
        artifact_repository=FakeArtifactRepository(),
        approval_repository=FakeApprovalRepository(),
        transition_recorder=transition_recorder,
        run_stepper=ApprovalStepper(run_repository, transition_recorder),
    )
    run = AgentRun.create(workflow="test", question="Q")
    run.status = RunStatus.QUEUED
    run_repository.save(run, TenantScope.local())

    result = await service.run_to_pause_or_completion(TenantScope.local(), run.run_id)

    assert result.status == RunStatus.AWAITING_APPROVAL


@pytest.mark.asyncio
async def test_lifecycle_service_run_to_pause_or_completion_stops_on_failure(run_repository, transition_recorder):
    service = RunLifecycleService(
        run_repository=run_repository,
        event_repository=FakeEventRepository(),
        artifact_repository=FakeArtifactRepository(),
        approval_repository=FakeApprovalRepository(),
        transition_recorder=transition_recorder,
        run_stepper=FailingStepper(run_repository, transition_recorder),
    )
    run = AgentRun.create(workflow="test", question="Q")
    run.status = RunStatus.QUEUED
    run_repository.save(run, TenantScope.local())

    result = await service.run_to_pause_or_completion(TenantScope.local(), run.run_id)

    assert result.status == RunStatus.FAILED


@pytest.mark.asyncio
async def test_lifecycle_service_run_to_pause_or_completion_respects_max_rounds(run_repository, transition_recorder):
    service = RunLifecycleService(
        run_repository=run_repository,
        event_repository=FakeEventRepository(),
        artifact_repository=FakeArtifactRepository(),
        approval_repository=FakeApprovalRepository(),
        transition_recorder=transition_recorder,
        run_stepper=LoopingStepper(run_repository, transition_recorder),
    )
    run = AgentRun.create(workflow="test", question="Q")
    run.status = RunStatus.QUEUED
    run.model_policy = ModelPolicy(max_tool_rounds=3)
    run_repository.save(run, TenantScope.local())

    result = await service.run_to_pause_or_completion(TenantScope.local(), run.run_id)

    assert result.status == RunStatus.FAILED


@pytest.mark.asyncio
async def test_lifecycle_service_queue_run_transitions_to_queued(lifecycle_service, run_repository):
    run = AgentRun.create(workflow="test", question="Q")
    run.status = RunStatus.CREATED
    run_repository.save(run, TenantScope.local())

    result = await lifecycle_service.queue_run(TenantScope.local(), run.run_id, "test-reason")

    assert result.status == RunStatus.QUEUED


@pytest.mark.asyncio
async def test_lifecycle_service_queue_run_is_idempotent_when_already_queued(lifecycle_service, run_repository):
    run = AgentRun.create(workflow="test", question="Q")
    run.status = RunStatus.QUEUED
    run_repository.save(run, TenantScope.local())

    result = await lifecycle_service.queue_run(TenantScope.local(), run.run_id, "test-reason")

    assert result.status == RunStatus.QUEUED


@pytest.mark.asyncio
async def test_lifecycle_service_queue_run_is_idempotent_when_completed(lifecycle_service, run_repository):
    run = AgentRun.create(workflow="test", question="Q")
    run.status = RunStatus.COMPLETED
    run_repository.save(run, TenantScope.local())

    result = await lifecycle_service.queue_run(TenantScope.local(), run.run_id, "test-reason")

    assert result.status == RunStatus.COMPLETED


@pytest.mark.asyncio
async def test_lifecycle_service_cancel_run_transitions_to_cancelling(lifecycle_service, run_repository):
    run = AgentRun.create(workflow="test", question="Q")
    run.status = RunStatus.QUEUED
    run_repository.save(run, TenantScope.local())

    result = await lifecycle_service.cancel_run(TenantScope.local(), run.run_id)

    assert result.status == RunStatus.CANCELLING
    assert result.cancel_requested_at is not None


@pytest.mark.asyncio
async def test_lifecycle_service_cancel_run_is_idempotent_when_completed(lifecycle_service, run_repository):
    run = AgentRun.create(workflow="test", question="Q")
    run.status = RunStatus.COMPLETED
    run_repository.save(run, TenantScope.local())

    result = await lifecycle_service.cancel_run(TenantScope.local(), run.run_id)

    assert result.status == RunStatus.COMPLETED


@pytest.mark.asyncio
async def test_lifecycle_service_cancel_run_is_idempotent_when_already_cancelling(lifecycle_service, run_repository):
    run = AgentRun.create(workflow="test", question="Q")
    run.status = RunStatus.CANCELLING
    run_repository.save(run, TenantScope.local())

    result = await lifecycle_service.cancel_run(TenantScope.local(), run.run_id)

    assert result.status == RunStatus.CANCELLING


@pytest.mark.asyncio
async def test_lifecycle_service_finalize_cancelled_transitions_to_cancelled(lifecycle_service, run_repository):
    run = AgentRun.create(workflow="test", question="Q")
    run.status = RunStatus.CANCELLING
    run_repository.save(run, TenantScope.local())

    result = await lifecycle_service.finalize_cancelled(TenantScope.local(), run.run_id)

    assert result.status == RunStatus.CANCELLED


@pytest.mark.asyncio
async def test_lifecycle_service_finalize_cancelled_is_idempotent_when_completed(lifecycle_service, run_repository):
    run = AgentRun.create(workflow="test", question="Q")
    run.status = RunStatus.COMPLETED
    run_repository.save(run, TenantScope.local())

    result = await lifecycle_service.finalize_cancelled(TenantScope.local(), run.run_id)

    assert result.status == RunStatus.COMPLETED


@pytest.mark.asyncio
async def test_lifecycle_service_record_failure_transitions_to_failed(lifecycle_service, run_repository):
    run = AgentRun.create(workflow="test", question="Q")
    run.status = RunStatus.QUEUED
    run_repository.save(run, TenantScope.local())

    result = await lifecycle_service.record_failure(TenantScope.local(), run.run_id, "something broke")

    assert result.status == RunStatus.FAILED


@pytest.mark.asyncio
async def test_lifecycle_service_record_failure_is_idempotent_when_already_failed(lifecycle_service, run_repository):
    run = AgentRun.create(workflow="test", question="Q")
    run.status = RunStatus.FAILED
    run_repository.save(run, TenantScope.local())

    result = await lifecycle_service.record_failure(TenantScope.local(), run.run_id, "something broke")

    assert result.status == RunStatus.FAILED


@pytest.mark.asyncio
async def test_lifecycle_service_record_failure_is_idempotent_when_completed(lifecycle_service, run_repository):
    run = AgentRun.create(workflow="test", question="Q")
    run.status = RunStatus.COMPLETED
    run_repository.save(run, TenantScope.local())

    result = await lifecycle_service.record_failure(TenantScope.local(), run.run_id, "something broke")

    assert result.status == RunStatus.COMPLETED


def test_lifecycle_service_get_run_returns_run(lifecycle_service, run_repository):
    run = AgentRun.create(workflow="test", question="Q")
    run_repository.save(run, TenantScope.local())

    result = lifecycle_service.get_run(TenantScope.local(), run.run_id)

    assert result is not None
    assert result.run_id == run.run_id


def test_lifecycle_service_get_run_returns_none_when_not_found(lifecycle_service):
    result = lifecycle_service.get_run(TenantScope.local(), "nonexistent")

    assert result is None


def test_lifecycle_service_list_events_returns_events_for_run(lifecycle_service, event_repository):
    run = AgentRun.create(workflow="test", question="Q")
    event = AgentEvent(event_id="e1", run_id=run.run_id, event_type=EventType.RUN_CREATED, sequence=1)
    event_repository.events.append(event)

    result = lifecycle_service.list_events(TenantScope.local(), run.run_id)

    assert len(result) == 1
    assert result[0].event_id == "e1"


def test_lifecycle_service_list_runs_returns_runs(lifecycle_service, run_repository):
    run1 = AgentRun.create(workflow="test", question="Q1")
    run2 = AgentRun.create(workflow="test", question="Q2")
    run_repository.save(run1, TenantScope.local())
    run_repository.save(run2, TenantScope.local())

    result = lifecycle_service.list_runs(TenantScope.local(), limit=10)

    assert len(result) == 2


def test_lifecycle_service_list_runs_by_session(lifecycle_service, run_repository):
    run = AgentRun.create(workflow="test", question="Q", session_id="ses-1")
    run_repository.save(run, TenantScope.local())
    run_repository._session_runs["ses-1"] = [run]

    result = lifecycle_service.list_runs(TenantScope.local(), session_id="ses-1")

    assert len(result) == 1
    assert result[0].session_id == "ses-1"


def test_lifecycle_service_list_runs_by_session_honors_limit(lifecycle_service, run_repository):
    runs = [
        AgentRun.create(workflow="test", question=f"Q{index}", session_id="ses-1")
        for index in range(3)
    ]
    for run in runs:
        run_repository.save(run, TenantScope.local())
    run_repository._session_runs["ses-1"] = runs

    result = lifecycle_service.list_runs(TenantScope.local(), session_id="ses-1", limit=1)

    assert [item.run_id for item in result] == [runs[0].run_id]


def test_lifecycle_service_list_artifacts_returns_artifacts(lifecycle_service, artifact_repository):
    run = AgentRun.create(workflow="test", question="Q")
    artifact = run.add_artifact(kind="memo", title="T", content="C")
    artifact_repository.artifacts.append(artifact)

    result = lifecycle_service.list_artifacts(TenantScope.local(), run.run_id)

    assert len(result) == 1
    assert result[0].artifact_id == artifact.artifact_id

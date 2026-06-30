"""Unit tests for RunStepper."""

from __future__ import annotations

import pytest

from doge.application.agent.artifact_finalizer import ArtifactFinalizer
from doge.application.agent.context_builder import ContextBuilder
from doge.application.agent.model_response_assembler import ModelResponseAssembler
from doge.application.agent.run_stepper import RunStepper
from doge.application.agent.transition_recorder import TransitionRecorder
from doge.core.domain.agent_models import AgentRun, EventType, RunStatus
from doge.core.domain.enterprise_context import EnterpriseContext
from doge.core.domain.model_policy import ModelPolicy
from doge.core.domain.run_execution_context import RunExecutionContext
from doge.core.ports.agent_model import AgentMessage, AgentResponse
from doge.core.ports.agent_repository import (
    IApprovalRepository,
    IArtifactRepository,
    IEventRepository,
    IRunRepository,
)
from doge.core.ports.model_router import RoutingDecision
from doge.core.ports.runtime_services import IModelExecutionService, IToolExecutionService, ModelExecutionResult, ToolResult
from doge.shared.scope import TenantScope


class FakeRunRepository(IRunRepository):
    def __init__(self):
        self.runs = {}

    def save(self, run, scope=None):
        self.runs[run.run_id] = run

    def get(self, run_id, *, tenant_id=None):
        return self.runs.get(run_id)

    def get_run_header(self, run_id, *, tenant_id=None):
        return self.runs.get(run_id)

    def list_by_session(self, session_id, scope=None):
        return []

    def list_recent(self, scope=None, limit=20):
        return []


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


class ConnectedFakeTxFactory:
    """Fake transaction factory that writes to fake repos on commit."""

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


class FakeContextBuilder:
    def build(self, run, events, *, enterprise_context=None, execution_context=None):
        return []


class FakeModelExecutionService(IModelExecutionService):
    def __init__(self, response_content="final memo"):
        self.response_content = response_content
        self.calls = []

    async def execute(self, *, run, policy, messages, tool_schemas_for, enterprise_context=None, execution_context=None):
        self.calls.append({"run": run, "messages": messages})
        return ModelExecutionResult(
            response=AgentResponse(
                message=AgentMessage(role="assistant", content=self.response_content)
            ),
            routing=None,
            routing_payload={},
        )


class FakeToolExecutionService(IToolExecutionService):
    def __init__(self):
        self.calls = []
        self._schemas = []

    def schemas_for(self, routing, context=None):
        return self._schemas

    async def execute(self, *, context, tool_name, arguments, run_id, timeout_seconds, request_id):
        self.calls.append({"tool_name": tool_name, "arguments": arguments})
        return ToolResult(name=tool_name, data={"result": "ok"})

    def audit(self, context, event_type, resource_type, resource_id, metadata=None, *, request_id=None):
        pass


class FakeArtifactEvaluationService:
    def artifact_content(self, content):
        return content or ""

    def metrics(self, artifact_text, events):
        return {}


class ToolCallModelExecutionService(IModelExecutionService):
    def __init__(self, tool_name="stock_overview", tool_args='{"ticker":"AAPL"}'):
        self.tool_name = tool_name
        self.tool_args = tool_args

    async def execute(self, *, run, policy, messages, tool_schemas_for, enterprise_context=None, execution_context=None):
        return ModelExecutionResult(
            response=AgentResponse(
                message=AgentMessage(
                    role="assistant",
                    content="",
                    tool_calls=[{
                        "id": "tc-1",
                        "type": "function",
                        "function": {
                            "name": self.tool_name,
                            "arguments": self.tool_args,
                        },
                    }],
                )
            ),
            routing=None,
            routing_payload={},
        )


class ApprovalToolModelExecutionService(IModelExecutionService):
    async def execute(self, *, run, policy, messages, tool_schemas_for, enterprise_context=None, execution_context=None):
        return ModelExecutionResult(
            response=AgentResponse(
                message=AgentMessage(
                    role="assistant",
                    content="",
                    tool_calls=[{
                        "id": "tc-1",
                        "type": "function",
                        "function": {
                            "name": "request_approval",
                            "arguments": '{"action":"publish","risk_level":"high"}',
                        },
                    }],
                )
            ),
            routing=None,
            routing_payload={},
        )


class BudgetExceededModelExecutionService(IModelExecutionService):
    async def execute(self, *, run, policy, messages, tool_schemas_for, enterprise_context=None, execution_context=None):
        return ModelExecutionResult(
            response=AgentResponse(
                message=AgentMessage(role="assistant", content="partial")
            ),
            routing=None,
            routing_payload={},
            budget_exceeded=True,
        )


class NullResponseModelExecutionService(IModelExecutionService):
    async def execute(self, *, run, policy, messages, tool_schemas_for, enterprise_context=None, execution_context=None):
        return ModelExecutionResult(
            response=None,
            routing=None,
            routing_payload={},
        )


@pytest.fixture
def run():
    r = AgentRun.create(workflow="test", question="Q")
    r.status = RunStatus.QUEUED
    return r


@pytest.fixture
def run_repository(run):
    repo = FakeRunRepository()
    repo.save(run, TenantScope.local())
    return repo


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
def artifact_finalizer():
    return ArtifactFinalizer(evaluation_service=FakeArtifactEvaluationService())


@pytest.fixture
def stepper(run_repository, event_repository, artifact_repository, approval_repository, transition_recorder, artifact_finalizer):
    return RunStepper(
        run_repository=run_repository,
        event_repository=event_repository,
        artifact_repository=artifact_repository,
        approval_repository=approval_repository,
        context_builder=FakeContextBuilder(),
        response_assembler=ModelResponseAssembler(),
        model_execution_service=FakeModelExecutionService(),
        tool_execution_service=FakeToolExecutionService(),
        artifact_finalizer=artifact_finalizer,
        transition_recorder=transition_recorder,
        citation_assembler=None,
    )


@pytest.mark.asyncio
async def test_run_stepper_step_completes_run_when_model_returns_content(stepper, run_repository, run):
    run.status = RunStatus.QUEUED
    run_repository.save(run, TenantScope.local())

    result = await stepper.step(TenantScope.local(), run.run_id)

    assert result.status == RunStatus.COMPLETED
    assert len(result.artifacts) == 1


@pytest.mark.asyncio
async def test_run_stepper_step_records_model_response_event(stepper, run_repository, run):
    run.status = RunStatus.QUEUED
    run_repository.save(run, TenantScope.local())

    await stepper.step(TenantScope.local(), run.run_id)

    assert any(e.event_type == EventType.MODEL_RESPONSE for e in run.events)


@pytest.mark.asyncio
async def test_run_stepper_step_records_artifact_created_event(stepper, run_repository, run):
    run.status = RunStatus.QUEUED
    run_repository.save(run, TenantScope.local())

    await stepper.step(TenantScope.local(), run.run_id)

    assert any(e.event_type == EventType.ARTIFACT_CREATED for e in run.events)


@pytest.mark.asyncio
async def test_run_stepper_step_returns_unchanged_when_already_completed(stepper, run_repository, run):
    run.status = RunStatus.COMPLETED
    run_repository.save(run, TenantScope.local())

    result = await stepper.step(TenantScope.local(), run.run_id)

    assert result.status == RunStatus.COMPLETED


@pytest.mark.asyncio
async def test_run_stepper_step_cancels_when_status_is_cancelling(stepper, run_repository, run):
    run.status = RunStatus.CANCELLING
    run_repository.save(run, TenantScope.local())

    result = await stepper.step(TenantScope.local(), run.run_id)

    assert result.status == RunStatus.CANCELLED


@pytest.mark.asyncio
async def test_run_stepper_step_fails_when_model_returns_none(run_repository, event_repository, artifact_repository, approval_repository, transition_recorder, artifact_finalizer):
    stepper = RunStepper(
        run_repository=run_repository,
        event_repository=event_repository,
        artifact_repository=artifact_repository,
        approval_repository=approval_repository,
        context_builder=FakeContextBuilder(),
        response_assembler=ModelResponseAssembler(),
        model_execution_service=NullResponseModelExecutionService(),
        tool_execution_service=FakeToolExecutionService(),
        artifact_finalizer=artifact_finalizer,
        transition_recorder=transition_recorder,
        citation_assembler=None,
    )
    run = AgentRun.create(workflow="test", question="Q")
    run.status = RunStatus.QUEUED
    run_repository.save(run, TenantScope.local())

    result = await stepper.step(TenantScope.local(), run.run_id)

    assert result.status == RunStatus.FAILED


@pytest.mark.asyncio
async def test_run_stepper_step_fails_when_budget_exceeded(run_repository, event_repository, artifact_repository, approval_repository, transition_recorder, artifact_finalizer):
    stepper = RunStepper(
        run_repository=run_repository,
        event_repository=event_repository,
        artifact_repository=artifact_repository,
        approval_repository=approval_repository,
        context_builder=FakeContextBuilder(),
        response_assembler=ModelResponseAssembler(),
        model_execution_service=BudgetExceededModelExecutionService(),
        tool_execution_service=FakeToolExecutionService(),
        artifact_finalizer=artifact_finalizer,
        transition_recorder=transition_recorder,
        citation_assembler=None,
    )
    run = AgentRun.create(workflow="test", question="Q")
    run.status = RunStatus.QUEUED
    run_repository.save(run, TenantScope.local())

    result = await stepper.step(TenantScope.local(), run.run_id)

    assert result.status == RunStatus.FAILED


@pytest.mark.asyncio
async def test_run_stepper_step_executes_tool_and_records_tool_events(run_repository, event_repository, artifact_repository, approval_repository, transition_recorder, artifact_finalizer):
    tool_service = FakeToolExecutionService()
    stepper = RunStepper(
        run_repository=run_repository,
        event_repository=event_repository,
        artifact_repository=artifact_repository,
        approval_repository=approval_repository,
        context_builder=FakeContextBuilder(),
        response_assembler=ModelResponseAssembler(),
        model_execution_service=ToolCallModelExecutionService(),
        tool_execution_service=tool_service,
        artifact_finalizer=artifact_finalizer,
        transition_recorder=transition_recorder,
        citation_assembler=None,
    )
    run = AgentRun.create(workflow="test", question="Q")
    run.status = RunStatus.QUEUED
    run_repository.save(run, TenantScope.local())

    result = await stepper.step(TenantScope.local(), run.run_id)

    assert result.status == RunStatus.RUNNING
    assert any(e.event_type == EventType.TOOL_CALL for e in run.events)
    assert any(e.event_type == EventType.TOOL_RESULT for e in run.events)
    assert len(tool_service.calls) == 1
    assert tool_service.calls[0]["tool_name"] == "stock_overview"


@pytest.mark.asyncio
async def test_run_stepper_step_requests_approval_when_tool_returns_approval_required(run_repository, event_repository, artifact_repository, approval_repository, transition_recorder, artifact_finalizer):
    class ApprovalToolService(FakeToolExecutionService):
        async def execute(self, *, context, tool_name, arguments, run_id, timeout_seconds, request_id):
            return ToolResult(
                name=tool_name,
                data={"approval_required": True, "action": "publish", "risk_level": "high"},
            )

    stepper = RunStepper(
        run_repository=run_repository,
        event_repository=event_repository,
        artifact_repository=artifact_repository,
        approval_repository=approval_repository,
        context_builder=FakeContextBuilder(),
        response_assembler=ModelResponseAssembler(),
        model_execution_service=ApprovalToolModelExecutionService(),
        tool_execution_service=ApprovalToolService(),
        artifact_finalizer=artifact_finalizer,
        transition_recorder=transition_recorder,
        citation_assembler=None,
    )
    run = AgentRun.create(workflow="test", question="Q")
    run.status = RunStatus.QUEUED
    run_repository.save(run, TenantScope.local())

    result = await stepper.step(TenantScope.local(), run.run_id)

    assert result.status == RunStatus.AWAITING_APPROVAL
    assert len(result.approvals) == 1
    assert result.approvals[0].action == "publish"
    assert any(e.event_type == EventType.APPROVAL_REQUESTED for e in run.events)


@pytest.mark.asyncio
async def test_run_stepper_step_cancels_mid_tool_execution(run_repository, event_repository, artifact_repository, approval_repository, transition_recorder, artifact_finalizer):
    class CancellingRunRepository(FakeRunRepository):
        def __init__(self, run):
            super().__init__()
            self._run = run
            self.call_count = 0

        def get(self, run_id, *, tenant_id=None):
            self.call_count += 1
            if self.call_count >= 3:
                self._run.status = RunStatus.CANCELLING
            return self._run

        def get_run_header(self, run_id, *, tenant_id=None):
            return self.get(run_id, tenant_id=tenant_id)

    run = AgentRun.create(workflow="test", question="Q")
    run.status = RunStatus.QUEUED
    canc_repo = CancellingRunRepository(run)
    canc_repo.save(run, TenantScope.local())

    stepper = RunStepper(
        run_repository=canc_repo,
        event_repository=event_repository,
        artifact_repository=artifact_repository,
        approval_repository=approval_repository,
        context_builder=FakeContextBuilder(),
        response_assembler=ModelResponseAssembler(),
        model_execution_service=ToolCallModelExecutionService(),
        tool_execution_service=FakeToolExecutionService(),
        artifact_finalizer=artifact_finalizer,
        transition_recorder=transition_recorder,
        citation_assembler=None,
    )

    result = await stepper.step(TenantScope.local(), run.run_id)

    assert result.status == RunStatus.CANCELLED


@pytest.mark.asyncio
async def test_run_stepper_step_raises_when_run_not_found(stepper):
    with pytest.raises(KeyError, match="run not found"):
        await stepper.step(TenantScope.local(), "nonexistent")

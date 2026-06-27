"""Unit tests for RuntimeKernel as a thin facade delegating to collaborators."""

from __future__ import annotations

import pytest

from doge.application.agent.runtime_kernel import RuntimeKernel
from doge.core.domain.agent_models import AgentRun, EventType, RunStatus
from doge.core.ports.runtime_services import (
    IApprovalCoordinator,
    IArtifactFinalizer,
    IRunLifecycleService,
    IRunStepper,
    ITransitionRecorder,
)
from doge.shared.scope import TenantScope


class FakeLifecycleService(IRunLifecycleService):
    def __init__(self):
        self.calls = []
        self._runs = {}
        self._events = {}
        self._artifacts = {}

    async def create_run(self, request, *, tenant_id=None):
        self.calls.append(("create_run", request, tenant_id))
        run = AgentRun.create(workflow=request.get("workflow", "test"), question=request.get("question", ""))
        self._runs[run.run_id] = run
        return run

    async def run_to_pause_or_completion(self, run_id, *, tenant_id=None):
        self.calls.append(("run_to_pause_or_completion", run_id, tenant_id))
        run = self._runs.get(run_id)
        if run:
            run.status = RunStatus.COMPLETED
        return run

    async def queue_run(self, scope, run_id=None, reason="queued", *, tenant_id=None):
        self.calls.append(("queue_run", scope, run_id, reason, tenant_id))
        run = self._runs.get(run_id)
        if run:
            run.status = RunStatus.QUEUED
        return run

    async def cancel_run(self, scope, run_id=None, *, tenant_id=None):
        self.calls.append(("cancel_run", scope, run_id, tenant_id))
        run = self._runs.get(run_id)
        if run:
            run.status = RunStatus.CANCELLING
        return run

    async def finalize_cancelled(self, scope, run_id=None, *, tenant_id=None):
        self.calls.append(("finalize_cancelled", scope, run_id, tenant_id))
        run = self._runs.get(run_id)
        if run:
            run.status = RunStatus.CANCELLED
        return run

    async def record_failure(self, scope, run_id=None, message=None, *, tenant_id=None):
        self.calls.append(("record_failure", scope, run_id, message, tenant_id))
        run = self._runs.get(run_id)
        if run:
            run.status = RunStatus.FAILED
        return run

    def get_run(self, scope, run_id=None, *, tenant_id=None):
        self.calls.append(("get_run", scope, run_id, tenant_id))
        return self._runs.get(run_id)

    def list_events(self, scope, run_id=None, *, tenant_id=None):
        self.calls.append(("list_events", scope, run_id, tenant_id))
        return self._events.get(run_id, [])

    def list_runs(self, scope=None, session_id=None, limit=20, *, tenant_id=None):
        self.calls.append(("list_runs", scope, session_id, limit, tenant_id))
        return list(self._runs.values())[:limit]

    def list_artifacts(self, scope, run_id=None, *, tenant_id=None):
        self.calls.append(("list_artifacts", scope, run_id, tenant_id))
        return self._artifacts.get(run_id, [])


class FakeStepper(IRunStepper):
    def __init__(self):
        self.calls = []

    async def step(self, run_id, *, tenant_id=None):
        self.calls.append(("step", run_id, tenant_id))
        return AgentRun.create(workflow="test", question="Q")


class FakeApprovalCoordinator(IApprovalCoordinator):
    def __init__(self):
        self.calls = []

    async def resolve(self, scope, run_id, approval_id, approved, *, tenant_id=None):
        self.calls.append(("resolve", scope, run_id, approval_id, approved, tenant_id))
        return AgentRun.create(workflow="test", question="Q")


class FakeTransitionRecorder(ITransitionRecorder):
    def __init__(self):
        self.calls = []

    async def record(self, run, *, status=None, events=None, artifacts=None, approvals=None, save_run=False):
        self.calls.append(("record", run, status, events, artifacts, approvals, save_run))
        return []


class FakeArtifactFinalizer(IArtifactFinalizer):
    def __init__(self):
        self.calls = []

    def build_artifact(self, run, response_content, events, *, usage=None):
        self.calls.append(("build_artifact", run, response_content, events, usage))
        from doge.core.domain.agent_models import AgentArtifact
        return AgentArtifact(artifact_id="art-1", kind="memo", title="T", content="C", run_id=run.run_id)


@pytest.fixture
def kernel():
    return RuntimeKernel(
        lifecycle_service=FakeLifecycleService(),
        stepper=FakeStepper(),
        transition_recorder=FakeTransitionRecorder(),
        approval_coordinator=FakeApprovalCoordinator(),
        artifact_finalizer=FakeArtifactFinalizer(),
    )


@pytest.fixture
def kernel_with_run():
    lifecycle = FakeLifecycleService()
    run = AgentRun.create(workflow="test", question="Q")
    lifecycle._runs[run.run_id] = run
    return RuntimeKernel(
        lifecycle_service=lifecycle,
        stepper=FakeStepper(),
        transition_recorder=FakeTransitionRecorder(),
        approval_coordinator=FakeApprovalCoordinator(),
        artifact_finalizer=FakeArtifactFinalizer(),
    ), run


@pytest.mark.asyncio
async def test_kernel_create_run_delegates_to_lifecycle_service(kernel):
    result = await kernel.create_run({"question": "Analyze AAPL"})

    assert result.question == "Analyze AAPL"
    assert kernel._lifecycle.calls[0][0] == "create_run"


@pytest.mark.asyncio
async def test_kernel_run_to_pause_or_completion_delegates_to_lifecycle_service(kernel_with_run):
    kernel, run = kernel_with_run
    result = await kernel.run_to_pause_or_completion(run.run_id)

    assert result.status == RunStatus.COMPLETED
    assert kernel._lifecycle.calls[0][0] == "run_to_pause_or_completion"
    assert kernel._lifecycle.calls[0][1] == run.run_id


@pytest.mark.asyncio
async def test_kernel_step_delegates_to_stepper(kernel):
    result = await kernel.step("run-1")

    assert kernel._stepper.calls[0][0] == "step"
    assert kernel._stepper.calls[0][1] == "run-1"


@pytest.mark.asyncio
async def test_kernel_resolve_approval_delegates_to_approval_coordinator(kernel):
    result = await kernel.resolve_approval("run-1", "appr-1", True)

    assert kernel._approval.calls[0][0] == "resolve"
    assert kernel._approval.calls[0][2] == "run-1"
    assert kernel._approval.calls[0][3] == "appr-1"
    assert kernel._approval.calls[0][4] is True


@pytest.mark.asyncio
async def test_kernel_cancel_run_delegates_to_lifecycle_service(kernel_with_run):
    kernel, run = kernel_with_run
    result = await kernel.cancel_run(run.run_id)

    assert result.status == RunStatus.CANCELLING
    assert kernel._lifecycle.calls[0][0] == "cancel_run"


@pytest.mark.asyncio
async def test_kernel_finalize_cancelled_delegates_to_lifecycle_service(kernel_with_run):
    kernel, run = kernel_with_run
    result = await kernel.finalize_cancelled(run.run_id)

    assert result.status == RunStatus.CANCELLED
    assert kernel._lifecycle.calls[0][0] == "finalize_cancelled"


@pytest.mark.asyncio
async def test_kernel_record_failure_delegates_to_lifecycle_service(kernel_with_run):
    kernel, run = kernel_with_run
    result = await kernel.record_failure(run.run_id, "something broke")

    assert result.status == RunStatus.FAILED
    assert kernel._lifecycle.calls[0][0] == "record_failure"


def test_kernel_get_run_delegates_to_lifecycle_service(kernel_with_run):
    kernel, run = kernel_with_run
    result = kernel.get_run(run.run_id)

    assert result is not None
    assert result.run_id == run.run_id
    assert kernel._lifecycle.calls[0][0] == "get_run"


def test_kernel_list_events_delegates_to_lifecycle_service(kernel_with_run):
    kernel, run = kernel_with_run
    result = kernel.list_events(run.run_id)

    assert result == []
    assert kernel._lifecycle.calls[0][0] == "list_events"


def test_kernel_list_runs_delegates_to_lifecycle_service(kernel_with_run):
    kernel, run = kernel_with_run
    result = kernel.list_runs(session_id="ses-1", limit=10)

    assert len(result) == 1
    assert kernel._lifecycle.calls[0][0] == "list_runs"
    assert kernel._lifecycle.calls[0][2] == "ses-1"
    assert kernel._lifecycle.calls[0][3] == 10


def test_kernel_list_artifacts_delegates_to_lifecycle_service(kernel_with_run):
    kernel, run = kernel_with_run
    result = kernel.list_artifacts(run.run_id)

    assert result == []
    assert kernel._lifecycle.calls[0][0] == "list_artifacts"


@pytest.mark.asyncio
async def test_kernel_queue_run_delegates_to_lifecycle_service(kernel_with_run):
    kernel, run = kernel_with_run
    result = await kernel.queue_run(run.run_id, reason="scheduled")

    assert result.status == RunStatus.QUEUED
    assert kernel._lifecycle.calls[0][0] == "queue_run"


@pytest.mark.asyncio
async def test_kernel_queue_run_with_legacy_signature(kernel_with_run):
    kernel, run = kernel_with_run
    result = await kernel.queue_run(TenantScope.local(), run.run_id, "scheduled")

    assert result.status == RunStatus.QUEUED
    assert kernel._lifecycle.calls[0][0] == "queue_run"


@pytest.mark.asyncio
async def test_kernel_resolve_approval_with_legacy_signature(kernel):
    result = await kernel.resolve_approval(TenantScope.local(), "run-1", "appr-1", True)

    assert kernel._approval.calls[0][0] == "resolve"
    assert kernel._approval.calls[0][1] == TenantScope.local()


def test_kernel_get_run_with_tenant_scope(kernel_with_run):
    kernel, run = kernel_with_run
    result = kernel.get_run(TenantScope.local(), run.run_id)

    assert result is not None


def test_kernel_list_runs_with_tenant_scope(kernel_with_run):
    kernel, run = kernel_with_run
    result = kernel.list_runs(TenantScope.local(), session_id="ses-1")

    assert len(result) == 1

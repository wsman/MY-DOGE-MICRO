import pytest

from doge.application.agent.approval_coordinator import ApprovalCoordinator
from doge.application.agent.artifact_finalizer import ArtifactFinalizer
from doge.application.agent.context_builder import ContextBuilder
from doge.application.agent.model_response_assembler import ModelResponseAssembler
from doge.application.agent.run_lifecycle_service import RunLifecycleService
from doge.application.agent.run_stepper import RunStepper
from doge.application.agent.runtime_kernel import RuntimeKernel
from doge.application.agent.transition_recorder import TransitionRecorder
from doge.application.agent.web_search_stage import WebSearchStage
from doge.application.tools import ToolRegistry, ToolResult
from doge.core.domain.agent_models import EventType, RunStatus
from doge.infrastructure.agent.scripted_model import ScriptedAgentModel
from doge.infrastructure.database.agent_repositories import (
    SQLiteApprovalRepository,
    SQLiteArtifactRepository,
    SQLiteEventRepository,
    SQLiteRunRepository,
)
from doge.infrastructure.database.sqlite_runtime_transaction import SQLiteRuntimeTransactionFactory
from doge.platform.runtime.services import (
    ArtifactEvaluationService,
    ModelExecutionService,
    ToolExecutionService,
)
from doge.shared.scope import TenantScope


def _schema(name: str):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": name,
            "parameters": {"type": "object", "properties": {}},
        },
    }


def _registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(_schema("stock_overview"), lambda **_: ToolResult("stock_overview", {"ticker": "AAPL"}))
    registry.register(_schema("get_portfolio_exposure"), lambda **kwargs: ToolResult(
        "get_portfolio_exposure",
        {"portfolio_id": kwargs.get("portfolio_id"), "holdings": []},
    ))
    registry.register(_schema("request_approval"), lambda **kwargs: ToolResult(
        "request_approval",
        {
            "approval_required": True,
            "action": kwargs.get("action", "publish"),
            "risk_level": kwargs.get("risk_level", "high"),
        },
    ))
    return registry


def _kernel(db_path) -> RuntimeKernel:
    repos = {
        "runs": SQLiteRunRepository(db_path),
        "events": SQLiteEventRepository(db_path),
        "artifacts": SQLiteArtifactRepository(db_path),
        "approvals": SQLiteApprovalRepository(db_path),
    }
    model = ScriptedAgentModel()
    response_assembler = ModelResponseAssembler()
    transition_recorder = TransitionRecorder(
        transaction_factory=SQLiteRuntimeTransactionFactory(db_path),
    )
    artifact_finalizer = ArtifactFinalizer(evaluation_service=ArtifactEvaluationService())
    stepper = RunStepper(
        run_repository=repos["runs"],
        event_repository=repos["events"],
        artifact_repository=repos["artifacts"],
        approval_repository=repos["approvals"],
        context_builder=ContextBuilder(
            document_repository=None,
            evidence_repository=None,
            session_repository=None,
            run_repository=repos["runs"],
        ),
        response_assembler=response_assembler,
        model_execution_service=ModelExecutionService(
            model=model,
            response_assembler=response_assembler,
            web_search_stage=WebSearchStage(model, response_assembler=response_assembler),
        ),
        tool_execution_service=ToolExecutionService(tool_registry=_registry()),
        artifact_finalizer=artifact_finalizer,
        transition_recorder=transition_recorder,
    )
    lifecycle = RunLifecycleService(
        run_repository=repos["runs"],
        event_repository=repos["events"],
        artifact_repository=repos["artifacts"],
        approval_repository=repos["approvals"],
        transition_recorder=transition_recorder,
        run_stepper=stepper,
    )
    return RuntimeKernel(
        lifecycle_service=lifecycle,
        stepper=stepper,
        transition_recorder=transition_recorder,
        approval_coordinator=ApprovalCoordinator(
            run_repository=repos["runs"],
            approval_repository=repos["approvals"],
            transition_recorder=transition_recorder,
        ),
        artifact_finalizer=artifact_finalizer,
    )


@pytest.mark.asyncio
async def test_direct_kernel_lifecycle_pauses_approves_resumes_and_persists_artifact(tmp_path):
    scope = TenantScope.local()
    kernel = _kernel(tmp_path / "agent_state.db")
    run = await kernel.create_run(scope, {"question": "Analyze AAPL"})

    paused = await kernel.run_to_pause_or_completion(scope, run.run_id)
    queued = await kernel.resolve_approval(scope, paused.run_id, paused.approvals[0].approval_id, True)
    completed = await kernel.run_to_pause_or_completion(scope, paused.run_id)

    assert paused.status == RunStatus.AWAITING_APPROVAL
    assert queued.status == RunStatus.QUEUED
    assert completed.status == RunStatus.COMPLETED
    assert completed.artifacts
    assert kernel.list_artifacts(scope, completed.run_id)[0].artifact_id == completed.artifacts[0].artifact_id


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("portfolio_id", "expects_portfolio_tool"),
    [(None, False), ("portfolio-explicit.v1", True)],
)
async def test_direct_kernel_scripted_portfolio_tool_requires_explicit_portfolio_id(
    tmp_path,
    portfolio_id,
    expects_portfolio_tool,
):
    scope = TenantScope.local()
    kernel = _kernel(tmp_path / "agent_state.db")
    request = {"question": "Analyze AAPL"}
    if portfolio_id:
        request["portfolio_id"] = portfolio_id
    run = await kernel.create_run(scope, request)

    paused = await kernel.run_to_pause_or_completion(scope, run.run_id)

    portfolio_results = [
        event.payload["result"]
        for event in paused.events
        if event.event_type == EventType.TOOL_RESULT
        and event.payload["result"]["name"] == "get_portfolio_exposure"
    ]
    assert bool(portfolio_results) is expects_portfolio_tool
    if expects_portfolio_tool:
        assert portfolio_results[0]["data"]["portfolio_id"] == portfolio_id


@pytest.mark.asyncio
async def test_direct_kernel_queue_resume_persists_run_queued_event(tmp_path):
    scope = TenantScope.local()
    kernel = _kernel(tmp_path / "agent_state.db")
    run = await kernel.create_run(scope, {"question": "Analyze AAPL"})

    queued = await kernel.queue_run(scope, run.run_id, "integration_resume")
    resumed = await kernel.resume_run(scope, queued.run_id)

    assert queued.status == RunStatus.QUEUED
    assert resumed.status in {RunStatus.AWAITING_APPROVAL, RunStatus.COMPLETED}
    assert any(event.event_type == EventType.RUN_QUEUED for event in resumed.events)


@pytest.mark.asyncio
async def test_direct_kernel_cancelling_run_finalizes_without_tool_events(tmp_path):
    scope = TenantScope.local()
    kernel = _kernel(tmp_path / "agent_state.db")
    run = await kernel.create_run(scope, {"question": "Analyze AAPL"})

    cancelling = await kernel.cancel_run(scope, run.run_id)
    cancelled = await kernel.step(scope, run.run_id)

    assert cancelling.status == RunStatus.CANCELLING
    assert cancelled.status == RunStatus.CANCELLED
    assert not any(event.event_type == EventType.TOOL_CALL for event in cancelled.events)
    assert any(event.event_type == EventType.RUN_CANCELLED for event in cancelled.events)


@pytest.mark.asyncio
async def test_direct_kernel_record_failure_and_tenant_scoped_reads_are_safe(tmp_path):
    tenant_a = TenantScope.enterprise("tenant-a", "user-a")
    tenant_b = TenantScope.enterprise("tenant-b", "user-b")
    kernel = _kernel(tmp_path / "agent_state.db")
    run = await kernel.create_run(tenant_a, {"question": "Analyze AAPL"})

    assert kernel.get_run(tenant_b, run.run_id) is None
    assert kernel.list_runs(tenant_b) == []
    failed = await kernel.record_failure(tenant_a, run.run_id, "secret-token-should-not-leak")

    assert failed.status == RunStatus.FAILED
    error_events = [event for event in failed.events if event.event_type == EventType.ERROR]
    assert error_events
    assert error_events[-1].payload["message"] == "runtime failure"
    assert "secret-token" not in repr(error_events[-1].payload)

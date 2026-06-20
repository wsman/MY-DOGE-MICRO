import pytest

from doge.application.agent.runtime_kernel import RuntimeKernel
from doge.application.agent.tools import ToolRegistry, ToolResult
from doge.core.domain.agent_models import EventType, RunStatus
from doge.infrastructure.agent.scripted_model import ScriptedAgentModel
from doge.infrastructure.database.agent_repositories import (
    SQLiteApprovalRepository,
    SQLiteArtifactRepository,
    SQLiteEventRepository,
    SQLiteRunRepository,
)


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
    registry.register(_schema("get_portfolio_exposure"), lambda **_: ToolResult(
        "get_portfolio_exposure",
        {"portfolio_id": "portfolio-demo", "holdings": []},
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


def _kernel(tmp_path):
    db = tmp_path / "agent_state.db"
    return RuntimeKernel(
        model=ScriptedAgentModel(),
        tool_registry=_registry(),
        run_repository=SQLiteRunRepository(db),
        event_repository=SQLiteEventRepository(db),
        artifact_repository=SQLiteArtifactRepository(db),
        approval_repository=SQLiteApprovalRepository(db),
    )


@pytest.mark.asyncio
async def test_kernel_create_run_persists_to_repository(tmp_path):
    kernel = _kernel(tmp_path)

    run = await kernel.create_run({"question": "Analyze AAPL", "session_id": "ses-1"})

    loaded = kernel.get_run(run.run_id)
    assert loaded is not None
    assert loaded.session_id == "ses-1"
    assert loaded.events[0].sequence == 1


@pytest.mark.asyncio
async def test_kernel_step_rebuilds_messages_from_events(tmp_path):
    kernel = _kernel(tmp_path)
    run = await kernel.create_run({"question": "Analyze AAPL"})

    await kernel.step(run.run_id)
    await kernel.step(run.run_id)

    loaded = kernel.get_run(run.run_id)
    assert loaded is not None
    assert [event.sequence for event in loaded.events] == sorted(event.sequence for event in loaded.events)
    assert any(event.payload.get("name") == "get_portfolio_exposure" for event in loaded.events)


@pytest.mark.asyncio
async def test_kernel_resolve_approval_resumes_loop(tmp_path):
    kernel = _kernel(tmp_path)
    run = await kernel.create_run({"question": "Analyze AAPL"})
    paused = await kernel.run_to_pause_or_completion(run.run_id)
    approval_id = paused.approvals[0].approval_id

    queued = await kernel.resolve_approval(paused.run_id, approval_id, True)
    completed = await kernel.run_to_pause_or_completion(paused.run_id)

    assert queued.status == RunStatus.QUEUED
    assert completed.status == RunStatus.COMPLETED
    assert completed.artifacts


@pytest.mark.asyncio
async def test_kernel_cancel_run_transitions_state_machine(tmp_path):
    kernel = _kernel(tmp_path)
    run = await kernel.create_run({"question": "Analyze AAPL"})

    cancelling = await kernel.cancel_run(run.run_id)

    assert cancelling.status == RunStatus.CANCELLING
    assert cancelling.cancel_requested_at is not None


@pytest.mark.asyncio
async def test_kernel_resolve_approval_denied_fails_run(tmp_path):
    kernel = _kernel(tmp_path)
    run = await kernel.create_run({"question": "Analyze AAPL"})
    paused = await kernel.run_to_pause_or_completion(run.run_id)

    failed = await kernel.resolve_approval(paused.run_id, paused.approvals[0].approval_id, False)

    assert failed.status == RunStatus.FAILED
    assert failed.artifacts == []
    assert any(
        event.event_type == EventType.APPROVAL_RESOLVED
        and event.payload.get("approved") is False
        for event in failed.events
    )
    assert all(event.event_type != EventType.ARTIFACT_CREATED for event in failed.events)


@pytest.mark.asyncio
async def test_kernel_cancel_completed_run_is_idempotent(tmp_path):
    kernel = _kernel(tmp_path)
    run = await kernel.create_run({"question": "Analyze AAPL"})
    paused = await kernel.run_to_pause_or_completion(run.run_id)
    await kernel.resolve_approval(paused.run_id, paused.approvals[0].approval_id, True)
    completed = await kernel.run_to_pause_or_completion(paused.run_id)
    event_count = len(completed.events)

    cancelled = await kernel.cancel_run(completed.run_id)

    assert cancelled.status == RunStatus.COMPLETED
    assert len(cancelled.events) == event_count
    assert all(event.event_type != EventType.RUN_CANCELLED for event in cancelled.events)


@pytest.mark.asyncio
async def test_kernel_step_cancels_mid_run(tmp_path):
    kernel = _kernel(tmp_path)
    run = await kernel.create_run({"question": "Analyze AAPL"})
    run.status = RunStatus.CANCELLING
    kernel._runs.save(run)

    cancelled = await kernel.step(run.run_id)

    assert cancelled.status == RunStatus.CANCELLED
    assert any(event.event_type == EventType.RUN_CANCELLED for event in cancelled.events)


@pytest.mark.asyncio
async def test_kernel_event_sequence_is_contiguous_and_ordered(tmp_path):
    kernel = _kernel(tmp_path)
    run = await kernel.create_run({"question": "Analyze AAPL"})
    paused = await kernel.run_to_pause_or_completion(run.run_id)
    await kernel.resolve_approval(paused.run_id, paused.approvals[0].approval_id, True)
    completed = await kernel.run_to_pause_or_completion(paused.run_id)

    events = completed.events
    event_types = [event.event_type for event in events]

    assert [event.sequence for event in events] == list(range(1, len(events) + 1))
    assert event_types[0] == EventType.RUN_CREATED
    assert event_types.index(EventType.APPROVAL_REQUESTED) < event_types.index(EventType.APPROVAL_RESOLVED)
    assert event_types.index(EventType.APPROVAL_RESOLVED) < event_types.index(EventType.RUN_QUEUED)
    assert event_types.index(EventType.RUN_QUEUED) < event_types.index(EventType.ARTIFACT_CREATED)
    assert event_types[-2:] == [EventType.MODEL_RESPONSE, EventType.ARTIFACT_CREATED]
    assert event_types.count(EventType.MODEL_RESPONSE) > 1
    assert event_types.count(EventType.TOOL_CALL) > 1
    assert event_types.count(EventType.TOOL_RESULT) > 1


@pytest.mark.asyncio
async def test_kernel_artifact_only_on_completed(tmp_path):
    kernel = _kernel(tmp_path)
    run = await kernel.create_run({"question": "Analyze AAPL"})
    paused = await kernel.run_to_pause_or_completion(run.run_id)

    assert paused.status == RunStatus.AWAITING_APPROVAL
    assert paused.artifacts == []

    queued = await kernel.resolve_approval(paused.run_id, paused.approvals[0].approval_id, True)
    completed = await kernel.run_to_pause_or_completion(paused.run_id)

    assert queued.status == RunStatus.QUEUED
    assert completed.status == RunStatus.COMPLETED
    assert len(completed.artifacts) == 1
    artifact = completed.artifacts[0]
    assert artifact.kind == "investment_memo"
    assert artifact.data["tool_execution_success"] == 1.0
    assert artifact.data["numerical_consistency"] is None
    assert artifact.data["citation_precision"] is None
    assert "usage" in artifact.data

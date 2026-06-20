import pytest

from doge.application.agent.runtime_kernel import RuntimeKernel
from doge.application.agent.tools import build_default_tool_registry
from doge.core.domain.agent_models import RunStatus
from doge.infrastructure.agent.scripted_model import ScriptedAgentModel
from doge.infrastructure.database.agent_repositories import (
    SQLiteApprovalRepository,
    SQLiteArtifactRepository,
    SQLiteEventRepository,
    SQLiteRunRepository,
)


def _kernel(tmp_path):
    db = tmp_path / "agent_state.db"
    return RuntimeKernel(
        model=ScriptedAgentModel(),
        tool_registry=build_default_tool_registry(),
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

    completed = await kernel.resolve_approval(paused.run_id, approval_id, True)

    assert completed.status == RunStatus.COMPLETED
    assert completed.artifacts


@pytest.mark.asyncio
async def test_kernel_cancel_run_transitions_state_machine(tmp_path):
    kernel = _kernel(tmp_path)
    run = await kernel.create_run({"question": "Analyze AAPL"})

    cancelled = await kernel.cancel_run(run.run_id)

    assert cancelled.status == RunStatus.CANCELLED

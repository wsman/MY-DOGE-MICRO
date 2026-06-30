"""Contract tests for approval pause/resume semantics."""

from __future__ import annotations

import pytest

from doge.core.domain.agent import EventType, RunStatus
from doge.shared.scope import TenantScope
from tests.unit.agent.test_runtime_kernel import _kernel


@pytest.mark.asyncio
async def test_approval_resolution_queues_and_resume_continues_agent_loop(tmp_path) -> None:
    kernel = _kernel(tmp_path)
    scope = TenantScope.local()
    run = await kernel.create_run(scope, {"question": "Analyze AAPL"})
    paused = await kernel.run_to_pause_or_completion(scope, run.run_id)

    assert paused.status == RunStatus.AWAITING_APPROVAL
    approval_id = paused.approvals[0].approval_id

    queued = await kernel.resolve_approval(scope, paused.run_id, approval_id, True)
    completed = await kernel.resume_run(scope, queued.run_id)
    event_types = [event.event_type for event in completed.events]

    assert queued.status == RunStatus.QUEUED
    assert completed.status == RunStatus.COMPLETED
    assert EventType.APPROVAL_RESOLVED in event_types
    assert EventType.RUN_QUEUED in event_types
    assert EventType.ARTIFACT_CREATED in event_types
    assert completed.artifacts

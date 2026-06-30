"""Contract tests for persisted agent events."""

from __future__ import annotations

from doge.core.domain.agent import AgentEvent, AgentRun, EventType
from doge.infrastructure.database.agent_repositories import SQLiteEventRepository, SQLiteRunRepository
from doge.shared.scope import TenantScope


def test_event_store_assigns_monotonic_sequences_and_filters_by_run(tmp_path) -> None:
    db = tmp_path / "agent_state.db"
    scope = TenantScope.local()
    run = AgentRun.create(workflow="investment_research", question="q")
    SQLiteRunRepository(db).save(run, scope)

    repo = SQLiteEventRepository(db)
    first = repo.append(AgentEvent(event_id="evt-1", run_id=run.run_id, event_type=EventType.RUN_CREATED))
    second = repo.append(AgentEvent(event_id="evt-2", run_id=run.run_id, event_type=EventType.MODEL_RESPONSE))

    loaded = repo.list_for_run(run.run_id)

    assert [first.sequence, second.sequence] == [1, 2]
    assert [event.event_id for event in loaded] == ["evt-1", "evt-2"]
    assert repo.list_for_run(run.run_id, after_sequence=1)[0].event_id == "evt-2"

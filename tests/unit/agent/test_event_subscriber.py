import asyncio

import pytest

from doge.core.domain.agent_models import AgentEvent, AgentRun, EventType
from doge.infrastructure.database.agent_repositories import SQLiteEventRepository, SQLiteRunRepository
from doge.infrastructure.database.event_subscriber import SQLiteEventSubscriber


@pytest.mark.asyncio
async def test_sqlite_event_subscriber_catches_up_and_polls_new_events(tmp_path):
    db = tmp_path / "agent_state.db"
    run = AgentRun.create(workflow="investment_research", question="q")
    SQLiteRunRepository(db).save(run)
    events = SQLiteEventRepository(db)
    first = events.append(AgentEvent(
        event_id="evt-1",
        run_id=run.run_id,
        event_type=EventType.RUN_CREATED,
        payload={"n": 1},
    ))
    subscriber = SQLiteEventSubscriber(db, poll_interval_seconds=0.01)
    received = []

    async def collect_two():
        async for event in subscriber.subscribe(run.run_id):
            received.append(event)
            if len(received) == 2:
                return

    task = asyncio.create_task(collect_two())
    await asyncio.sleep(0.03)
    second = events.append(AgentEvent(
        event_id="evt-2",
        run_id=run.run_id,
        event_type=EventType.MODEL_RESPONSE,
        payload={"n": 2},
    ))
    await asyncio.wait_for(task, timeout=1)

    assert [event.event_id for event in received] == [first.event_id, second.event_id]
    assert [event.sequence for event in received] == [1, 2]


@pytest.mark.asyncio
async def test_sqlite_event_subscriber_respects_after_sequence(tmp_path):
    db = tmp_path / "agent_state.db"
    run = AgentRun.create(workflow="investment_research", question="q")
    SQLiteRunRepository(db).save(run)
    events = SQLiteEventRepository(db)
    events.append(AgentEvent(
        event_id="evt-1",
        run_id=run.run_id,
        event_type=EventType.RUN_CREATED,
        payload={"n": 1},
    ))
    second = events.append(AgentEvent(
        event_id="evt-2",
        run_id=run.run_id,
        event_type=EventType.MODEL_RESPONSE,
        payload={"n": 2},
    ))
    subscriber = SQLiteEventSubscriber(db, poll_interval_seconds=0.01)

    async for event in subscriber.subscribe(run.run_id, after_sequence=1):
        received = event
        break

    assert received.event_id == second.event_id
    assert received.sequence == 2

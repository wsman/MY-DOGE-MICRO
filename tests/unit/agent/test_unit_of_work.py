import asyncio
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from doge.core.domain.agent_models import AgentSession, EventType, RunStatus
from doge.infrastructure.database.agent_repositories import (
    SQLiteIdempotencyStore,
    SQLiteRunQueue,
    SQLiteRunRepository,
    SQLiteSessionRepository,
)
from doge.infrastructure.database.sqlite_uow import SQLiteAgentUnitOfWork


def _create_session(db):
    session = AgentSession.create("Demo")
    SQLiteSessionRepository(db).save(session)
    return session


def _count(db, table: str) -> int:
    with sqlite3.connect(str(db)) as conn:
        return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def test_enqueue_emits_run_queued_and_sets_status_queued(tmp_path):
    db = tmp_path / "agent_state.db"
    session = _create_session(db)

    run_id = asyncio.run(
        SQLiteAgentUnitOfWork(db).enqueue_run_and_turn(
            session_id=session.session_id,
            message="Analyze AAPL",
            idempotency_key="key-1",
        )
    )

    run = SQLiteRunRepository(db).get(run_id)
    loaded_session = SQLiteSessionRepository(db).get(session.session_id)

    assert run is not None
    assert run.status == RunStatus.QUEUED
    assert [event.event_type for event in run.events] == [EventType.RUN_CREATED, EventType.RUN_QUEUED]
    assert SQLiteRunQueue(db).list_pending() == [run_id]
    assert SQLiteIdempotencyStore(db).get("key-1", session.session_id) == run_id
    assert loaded_session is not None
    assert len(loaded_session.turns) == 1
    assert loaded_session.turns[0].run_id == run_id


def test_concurrent_idempotent_enqueue_creates_single_run(tmp_path):
    db = tmp_path / "agent_state.db"
    session = _create_session(db)

    def enqueue_once(_):
        return asyncio.run(
            SQLiteAgentUnitOfWork(db).enqueue_run_and_turn(
                session_id=session.session_id,
                message="Analyze AAPL",
                idempotency_key="same-key",
            )
        )

    with ThreadPoolExecutor(max_workers=5) as executor:
        run_ids = list(executor.map(enqueue_once, range(5)))

    assert len(set(run_ids)) == 1
    assert _count(db, "runs") == 1
    assert _count(db, "turns") == 1
    assert _count(db, "events") == 2
    assert _count(db, "run_queue") == 1
    assert SQLiteIdempotencyStore(db).get("same-key", session.session_id) == run_ids[0]


def test_uow_failure_leaves_no_partial_state(tmp_path):
    db = tmp_path / "agent_state.db"
    session = _create_session(db)

    class FailingUnitOfWork(SQLiteAgentUnitOfWork):
        def _insert_turn(self, conn, turn) -> None:
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(
            FailingUnitOfWork(db).enqueue_run_and_turn(
                session_id=session.session_id,
                message="Analyze AAPL",
                idempotency_key="fail-key",
            )
        )

    assert _count(db, "runs") == 0
    assert _count(db, "turns") == 0
    assert _count(db, "events") == 0
    assert _count(db, "run_queue") == 0
    assert _count(db, "idempotency_keys") == 0

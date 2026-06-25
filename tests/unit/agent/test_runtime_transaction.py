import asyncio
import inspect
import sqlite3

import pytest

from doge.application.agent.runtime_kernel import RuntimeKernel
from doge.application.agent.outbox_publisher import OutboxPublisher
from doge.application.agent.tools import ToolRegistry
from doge.core.domain.agent_models import AgentSession, EventType, RunStatus
from doge.core.ports.agent_model import AgentMessage, AgentResponse
from doge.infrastructure.database.agent_repositories import (
    SQLiteApprovalRepository,
    SQLiteArtifactRepository,
    SQLiteEventRepository,
    SQLiteRunRepository,
    SQLiteSessionRepository,
)
from doge.infrastructure.database.sqlite_runtime_transaction import SQLiteRuntimeTransactionFactory
from doge.infrastructure.database.sqlite_runtime_transaction import SQLiteOutboxRepository
from doge.infrastructure.database.sqlite_uow import SQLiteAgentUnitOfWork
from doge.platform.runtime.services import (
    ArtifactEvaluationService,
    ModelExecutionService,
    ToolExecutionService,
)


class FinalModel:
    async def chat(self, messages, **kwargs):
        yield AgentResponse(message=AgentMessage(role="assistant", content="final memo"))


class CapturingPublisher:
    def __init__(self) -> None:
        self.events = []

    async def publish(self, event) -> None:
        self.events.append(event)


class FailingArtifactFactory:
    def __init__(self, db_path) -> None:
        self._inner = SQLiteRuntimeTransactionFactory(db_path)

    def begin(self):
        return FailingArtifactTransaction(self._inner.begin())


class FailingArtifactTransaction:
    def __init__(self, inner) -> None:
        self._inner = inner

    def save_artifact(self, artifact) -> None:
        raise RuntimeError("artifact write failed")

    def __getattr__(self, name):
        return getattr(self._inner, name)


def _kernel(db, *, transaction_factory=None):
    model = FinalModel()
    registry = ToolRegistry()
    return RuntimeKernel(
        model=model,
        tool_registry=registry,
        run_repository=SQLiteRunRepository(db),
        event_repository=SQLiteEventRepository(db),
        artifact_repository=SQLiteArtifactRepository(db),
        approval_repository=SQLiteApprovalRepository(db),
        model_execution_service=ModelExecutionService(model=model),
        tool_execution_service=ToolExecutionService(tool_registry=registry),
        artifact_evaluation_service=ArtifactEvaluationService(),
        runtime_transaction_factory=transaction_factory or SQLiteRuntimeTransactionFactory(db),
    )


def test_runtime_kernel_transitions_do_not_call_repositories_directly():
    source = inspect.getsource(RuntimeKernel)

    assert "self._runs.save" not in source
    assert "self._events.append" not in source
    assert "self._artifacts.save" not in source
    assert "self._approvals.save" not in source


def test_runtime_events_have_matching_outbox_rows(tmp_path):
    db = tmp_path / "agent_state.db"
    kernel = _kernel(db)

    run = asyncio.run(kernel.create_run({"question": "Analyze AAPL"}))
    completed = asyncio.run(kernel.step(run.run_id))

    assert completed.status == RunStatus.COMPLETED
    with sqlite3.connect(db) as conn:
        event_ids = [row[0] for row in conn.execute("SELECT event_id FROM events ORDER BY sequence").fetchall()]
        outbox_event_ids = [
            row[0]
            for row in conn.execute("SELECT event_id FROM runtime_outbox ORDER BY sequence").fetchall()
        ]

    assert event_ids == outbox_event_ids
    assert len(event_ids) == 3


def test_runtime_transition_rolls_back_event_and_outbox_when_artifact_save_fails(tmp_path):
    db = tmp_path / "agent_state.db"
    kernel = _kernel(db, transaction_factory=FailingArtifactFactory(db))
    run = asyncio.run(kernel.create_run({"question": "Analyze AAPL"}))

    with pytest.raises(RuntimeError, match="artifact write failed"):
        asyncio.run(kernel.step(run.run_id))

    loaded = kernel.get_run(run.run_id)
    events = kernel.list_events(run.run_id)
    with sqlite3.connect(db) as conn:
        artifacts = conn.execute("SELECT artifact_id FROM artifacts").fetchall()
        outbox_types = [
            row[0]
            for row in conn.execute(
                "SELECT json_extract(payload, '$.event_type') FROM runtime_outbox ORDER BY sequence"
            ).fetchall()
        ]

    assert loaded is not None
    assert loaded.status == RunStatus.RUNNING
    assert [event.event_type for event in events] == [EventType.RUN_CREATED, EventType.MODEL_RESPONSE]
    assert artifacts == []
    assert outbox_types == [EventType.RUN_CREATED.value, EventType.MODEL_RESPONSE.value]


def test_enqueue_unit_of_work_stages_outbox_for_initial_events(tmp_path):
    db = tmp_path / "agent_state.db"
    sessions = SQLiteSessionRepository(db)
    created = AgentSession.create("Demo")
    sessions.save(created)

    run_id = asyncio.run(
        SQLiteAgentUnitOfWork(db).enqueue_run_and_turn(
            session_id=created.session_id,
            message="Analyze AAPL",
        )
    )

    with sqlite3.connect(db) as conn:
        event_ids = [
            row[0]
            for row in conn.execute("SELECT event_id FROM events WHERE run_id = ? ORDER BY sequence", (run_id,))
            .fetchall()
        ]
        outbox_event_ids = [
            row[0]
            for row in conn.execute(
                "SELECT event_id FROM runtime_outbox WHERE run_id = ? ORDER BY sequence",
                (run_id,),
            ).fetchall()
        ]

    assert event_ids == outbox_event_ids
    assert len(event_ids) == 2


def test_outbox_publisher_claims_and_marks_events_published(tmp_path):
    db = tmp_path / "agent_state.db"
    kernel = _kernel(db)
    run = asyncio.run(kernel.create_run({"question": "Analyze AAPL"}))
    asyncio.run(kernel.step(run.run_id))
    publisher = CapturingPublisher()
    outbox_publisher = OutboxPublisher(
        SQLiteOutboxRepository(db),
        publisher,
        worker_id="test-publisher",
        batch_size=10,
    )

    published = asyncio.run(outbox_publisher.publish_once())

    with sqlite3.connect(db) as conn:
        statuses = [row[0] for row in conn.execute("SELECT status FROM runtime_outbox").fetchall()]

    assert published == 3
    assert [event.sequence for event in publisher.events] == [1, 2, 3]
    assert statuses == ["published", "published", "published"]

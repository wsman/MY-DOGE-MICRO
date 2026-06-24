"""SQLite unit-of-work implementation for agent run scheduling."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any
from uuid import uuid4

from doge.config import get_settings
from doge.core.domain.agent_models import AgentEvent, AgentRun, AgentTurn, EventType, RunStatus, utc_now
from doge.core.domain.enterprise_context import IdentitySnapshot
from doge.core.domain.model_policy import ModelPolicy
from doge.core.domain.run_execution_context import WorkflowRunContext
from doge.core.ports.event_publisher import IEventPublisher
from doge.core.ports.unit_of_work import IAgentUnitOfWork
from doge.infrastructure.database.agent_repositories import bootstrap_agent_schema


class _NoopEventPublisher:
    async def publish(self, event: AgentEvent) -> None:
        return None


class SQLiteAgentUnitOfWork(IAgentUnitOfWork):
    """SQLite transaction boundary for agent run enqueue workflows."""

    def __init__(
        self,
        db_path: Path | str | None = None,
        *,
        event_publisher: IEventPublisher | None = None,
    ) -> None:
        self._db_path = Path(db_path) if db_path is not None else get_settings().db.agent_db
        bootstrap_agent_schema(self._db_path)
        self._publisher = event_publisher or _NoopEventPublisher()

    async def enqueue_run_and_turn(
        self,
        *,
        session_id: str,
        message: str,
        workflow: str = "investment_research",
        market: str = "us",
        language: str = "en",
        document_ids: list[str] | None = None,
        portfolio_id: str | None = "portfolio-demo",
        model_policy: dict[str, Any] | None = None,
        identity_snapshot: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> str:
        run_id = f"run-{uuid4().hex[:12]}"
        events_to_publish: list[AgentEvent] = []
        with self._connect() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                existing = self._reserve_or_get(conn, idempotency_key, session_id, run_id)
                if existing is not None:
                    conn.commit()
                    return existing
                if conn.execute("SELECT 1 FROM sessions WHERE session_id = ?", (session_id,)).fetchone() is None:
                    raise KeyError(f"session not found: {session_id}")

                run = AgentRun.create(
                    run_id=run_id,
                    workflow=workflow,
                    question=message,
                    session_id=session_id,
                    market=market,
                    language=language,
                    document_ids=document_ids or [],
                    portfolio_id=portfolio_id,
                    model_policy=model_policy or {"max_tool_rounds": 8},
                    identity_snapshot=_identity_snapshot_from_inputs(identity_snapshot, model_policy),
                )
                tenant_id = _tenant_id_from_run(run)
                created_event = run.add_event(EventType.RUN_CREATED, {"question": run.question, "workflow": run.workflow})
                run.status = RunStatus.QUEUED
                run.updated_at = utc_now()
                queued_event = run.add_event(EventType.RUN_QUEUED, {"reason": "new_turn"})
                self._insert_run(conn, run, tenant_id=tenant_id)
                self._insert_turn(
                    conn,
                    AgentTurn.create(
                        session_id=session_id,
                        user_message=message,
                        run_id=run.run_id,
                        tenant_id=tenant_id,
                    ),
                )
                self._insert_event(conn, created_event, tenant_id=tenant_id)
                self._insert_outbox(conn, created_event)
                self._insert_event(conn, queued_event, tenant_id=tenant_id)
                self._insert_outbox(conn, queued_event)
                self._insert_queue_status(conn, run.run_id, "queued")
                self._touch_session(conn, session_id)
                conn.commit()
                events_to_publish = [created_event, queued_event]
            except Exception:
                conn.rollback()
                raise

        for event in events_to_publish:
            await self._publisher.publish(event)
        return run_id

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        return conn

    def _reserve_or_get(
        self,
        conn: sqlite3.Connection,
        key: str | None,
        scope: str,
        run_id: str,
    ) -> str | None:
        if not key:
            return None
        row = conn.execute(
            "SELECT run_id FROM idempotency_keys WHERE key = ? AND scope = ?",
            (key, scope),
        ).fetchone()
        if row is not None:
            return row["run_id"]
        conn.execute(
            """
            INSERT INTO idempotency_keys(key, scope, run_id, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (key, scope, run_id, utc_now()),
        )
        return None

    def _insert_run(self, conn: sqlite3.Connection, run: AgentRun, *, tenant_id: str | None = None) -> None:
        conn.execute(
            """
            INSERT INTO runs(
                run_id, tenant_id, session_id, workflow, question, market, language,
                document_ids, portfolio_id, model_policy, workflow_context, identity_snapshot, status,
                cancel_requested_at, created_at, updated_at, schema_version
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run.run_id,
                tenant_id,
                run.session_id,
                run.workflow,
                run.question,
                run.market,
                run.language,
                _json_dumps(run.document_ids),
                run.portfolio_id,
                _json_dumps(ModelPolicy.from_dict(run.model_policy).to_dict()),
                _workflow_context_json(run.workflow_context),
                _json_dumps(run.identity_snapshot.to_dict()) if run.identity_snapshot is not None else None,
                run.status.value,
                run.cancel_requested_at,
                run.created_at,
                run.updated_at,
                run.schema_version,
            ),
        )

    def _insert_turn(self, conn: sqlite3.Connection, turn: AgentTurn) -> None:
        conn.execute(
            """
            INSERT INTO turns(turn_id, session_id, tenant_id, user_message, run_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (turn.turn_id, turn.session_id, turn.tenant_id, turn.user_message, turn.run_id, turn.created_at),
        )

    def _insert_event(self, conn: sqlite3.Connection, event: AgentEvent, *, tenant_id: str | None = None) -> None:
        if event.sequence <= 0:
            event.sequence = _next_event_sequence(conn, event.run_id)
        conn.execute(
            """
            INSERT INTO events(event_id, tenant_id, run_id, event_type, payload, sequence, schema_version, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                tenant_id,
                event.run_id,
                event.event_type.value,
                _json_dumps(event.payload),
                event.sequence,
                event.schema_version,
                event.created_at,
            ),
        )

    def _insert_outbox(self, conn: sqlite3.Connection, event: AgentEvent) -> None:
        conn.execute(
            """
            INSERT INTO runtime_outbox(outbox_id, event_id, run_id, sequence, payload, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'pending', ?)
            """,
            (
                f"outbox-{uuid4().hex[:12]}",
                event.event_id,
                event.run_id,
                event.sequence,
                _event_payload(event),
                utc_now(),
            ),
        )

    def _insert_queue_status(self, conn: sqlite3.Connection, run_id: str, status: str) -> None:
        conn.execute(
            """
            INSERT INTO run_queue(run_id, status, created_at, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (run_id, status),
        )

    def _touch_session(self, conn: sqlite3.Connection, session_id: str) -> None:
        conn.execute("UPDATE sessions SET updated_at = ? WHERE session_id = ?", (utc_now(), session_id))


def _json_dumps(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=False)


def _event_payload(event: AgentEvent) -> str:
    return _json_dumps({
        "event_id": event.event_id,
        "run_id": event.run_id,
        "event_type": event.event_type.value,
        "payload": event.payload,
        "sequence": event.sequence,
        "schema_version": event.schema_version,
        "created_at": event.created_at,
    })


def _workflow_context_json(workflow_context: Any) -> str | None:
    if workflow_context is None:
        return None
    if isinstance(workflow_context, WorkflowRunContext):
        payload = workflow_context.to_dict()
    elif isinstance(workflow_context, dict):
        resolved = WorkflowRunContext.from_mapping(workflow_context)
        payload = resolved.to_dict() if resolved is not None else dict(workflow_context)
    else:
        return None
    return _json_dumps(payload)


def _identity_snapshot_from_inputs(
    identity_snapshot: dict[str, Any] | None,
    model_policy: dict[str, Any] | None,
) -> IdentitySnapshot | None:
    normalized = IdentitySnapshot.from_mapping(identity_snapshot)
    if normalized is not None:
        return normalized
    return IdentitySnapshot.from_mapping(model_policy)


def _tenant_id_from_run(run: AgentRun) -> str | None:
    if run.identity_snapshot is not None:
        return run.identity_snapshot.tenant_id
    legacy = IdentitySnapshot.from_mapping(ModelPolicy.from_dict(run.model_policy).extra)
    return legacy.tenant_id if legacy is not None and legacy.tenant_id != "local" else None


def _next_event_sequence(conn: sqlite3.Connection, run_id: str) -> int:
    row = conn.execute(
        "SELECT COALESCE(MAX(sequence), 0) + 1 AS next_sequence FROM events WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    return int(row["next_sequence"])

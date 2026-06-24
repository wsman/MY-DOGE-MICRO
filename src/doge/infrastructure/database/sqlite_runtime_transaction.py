from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from doge.config import get_settings
from doge.core.domain.agent_models import AgentApproval, AgentArtifact, AgentEvent, AgentRun, EventType, utc_now
from doge.core.domain.enterprise_context import IdentitySnapshot
from doge.core.domain.model_policy import ModelPolicy
from doge.core.domain.run_execution_context import WorkflowRunContext
from doge.core.ports.runtime_transaction import IOutboxRepository, IRuntimeTransaction, IRuntimeTransactionFactory
from doge.infrastructure.database.agent_repositories import bootstrap_agent_schema
from doge.infrastructure.database.tenant_guard import LOCAL_TENANT_ID, resolve_tenant_id


class SQLiteRuntimeTransactionFactory(IRuntimeTransactionFactory):
    def __init__(self, db_path: Path | str | None = None) -> None:
        self._db_path = Path(db_path) if db_path is not None else get_settings().db.agent_db
        bootstrap_agent_schema(self._db_path)

    def begin(self) -> IRuntimeTransaction:
        conn = sqlite3.connect(str(self._db_path), timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("BEGIN IMMEDIATE")
        return SQLiteRuntimeTransaction(conn)


class SQLiteRuntimeTransaction(IRuntimeTransaction):
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._closed = False

    def save_run(self, run: AgentRun) -> None:
        tenant_id = _tenant_id_from_run(run)
        self._conn.execute(
            """
            INSERT INTO runs(
                run_id, tenant_id, session_id, workflow, question, market, language,
                document_ids, portfolio_id, model_policy, workflow_context, identity_snapshot, status,
                cancel_requested_at, created_at, updated_at, schema_version
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                tenant_id = excluded.tenant_id,
                session_id = excluded.session_id,
                workflow = excluded.workflow,
                question = excluded.question,
                market = excluded.market,
                language = excluded.language,
                document_ids = excluded.document_ids,
                portfolio_id = excluded.portfolio_id,
                model_policy = excluded.model_policy,
                workflow_context = excluded.workflow_context,
                identity_snapshot = excluded.identity_snapshot,
                status = excluded.status,
                cancel_requested_at = excluded.cancel_requested_at,
                updated_at = excluded.updated_at,
                schema_version = excluded.schema_version
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
                _identity_snapshot_json(run.identity_snapshot),
                run.status.value,
                run.cancel_requested_at,
                run.created_at,
                run.updated_at,
                run.schema_version,
            ),
        )

    def append_event(self, event: AgentEvent) -> AgentEvent:
        tenant_id = _tenant_id_for_run(self._conn, event.run_id)
        if event.sequence <= 0:
            event.sequence = _next_event_sequence(self._conn, event.run_id)
        self._conn.execute(
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
        return event

    def save_artifact(self, artifact: AgentArtifact) -> None:
        tenant_id = _tenant_id_for_run(self._conn, artifact.run_id)
        self._conn.execute(
            """
            INSERT INTO artifacts(artifact_id, tenant_id, run_id, kind, title, content, data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(artifact_id) DO UPDATE SET
                tenant_id = excluded.tenant_id,
                run_id = excluded.run_id,
                kind = excluded.kind,
                title = excluded.title,
                content = excluded.content,
                data = excluded.data
            """,
            (
                artifact.artifact_id,
                tenant_id,
                artifact.run_id,
                artifact.kind,
                artifact.title,
                artifact.content,
                _json_dumps(artifact.data),
                artifact.created_at,
            ),
        )

    def save_approval(self, approval: AgentApproval) -> None:
        tenant_id = _tenant_id_for_run(self._conn, approval.run_id)
        self._conn.execute(
            """
            INSERT INTO approvals(approval_id, tenant_id, run_id, action, risk_level, status, created_at, resolved_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(approval_id) DO UPDATE SET
                tenant_id = excluded.tenant_id,
                run_id = excluded.run_id,
                action = excluded.action,
                risk_level = excluded.risk_level,
                status = excluded.status,
                resolved_at = excluded.resolved_at
            """,
            (
                approval.approval_id,
                tenant_id,
                approval.run_id,
                approval.action,
                approval.risk_level,
                approval.status,
                approval.created_at,
                approval.resolved_at,
            ),
        )

    def stage_outbox(self, event: AgentEvent) -> None:
        self._conn.execute(
            """
            INSERT INTO runtime_outbox(
                outbox_id, event_id, run_id, sequence, payload, status, created_at
            )
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

    def commit(self) -> None:
        if self._closed:
            return
        self._conn.commit()
        self._conn.close()
        self._closed = True

    def rollback(self) -> None:
        if self._closed:
            return
        self._conn.rollback()
        self._conn.close()
        self._closed = True


class SQLiteOutboxRepository(IOutboxRepository):
    def __init__(self, db_path: Path | str | None = None) -> None:
        self._db_path = Path(db_path) if db_path is not None else get_settings().db.agent_db
        bootstrap_agent_schema(self._db_path)

    def claim_pending(self, worker_id: str, batch_size: int, lease_seconds: int) -> list[AgentEvent]:
        now = utc_now()
        stale_before = _seconds_ago(lease_seconds)
        with self._connect() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                rows = conn.execute(
                    """
                    SELECT * FROM runtime_outbox
                    WHERE status = 'pending'
                       OR (status = 'leased' AND leased_at <= ?)
                    ORDER BY created_at ASC
                    LIMIT ?
                    """,
                    (stale_before, batch_size),
                ).fetchall()
                event_ids = [row["event_id"] for row in rows]
                if event_ids:
                    conn.executemany(
                        """
                        UPDATE runtime_outbox
                        SET status = 'leased', worker_id = ?, leased_at = ?
                        WHERE event_id = ?
                        """,
                        [(worker_id, now, event_id) for event_id in event_ids],
                    )
                conn.commit()
                return [_outbox_row_to_event(row) for row in rows]
            except Exception:
                conn.rollback()
                raise

    def mark_published(self, event_ids: list[str]) -> None:
        if not event_ids:
            return
        now = utc_now()
        with self._connect() as conn:
            conn.executemany(
                """
                UPDATE runtime_outbox
                SET status = 'published', published_at = ?
                WHERE event_id = ?
                """,
                [(now, event_id) for event_id in event_ids],
            )
            conn.commit()

    def release_stale(self, lease_timeout_seconds: int) -> int:
        stale_before = _seconds_ago(lease_timeout_seconds)
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE runtime_outbox
                SET status = 'pending', worker_id = NULL, leased_at = NULL
                WHERE status = 'leased' AND leased_at <= ?
                """,
                (stale_before,),
            )
            conn.commit()
            return int(cursor.rowcount or 0)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        return conn


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _identity_snapshot_json(snapshot: IdentitySnapshot | dict[str, Any] | None) -> str | None:
    normalized = IdentitySnapshot.from_mapping(snapshot)
    if normalized is None:
        return None
    return _json_dumps(normalized.to_dict())


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


def _tenant_id_from_run(run: AgentRun) -> str | None:
    if run.identity_snapshot is None:
        return LOCAL_TENANT_ID
    return resolve_tenant_id(run.identity_snapshot.tenant_id)


def _tenant_id_for_run(conn: sqlite3.Connection, run_id: str) -> str | None:
    row = conn.execute("SELECT tenant_id FROM runs WHERE run_id = ?", (run_id,)).fetchone()
    if row is None:
        return None
    tenant_id = row["tenant_id"]
    return str(tenant_id) if tenant_id else LOCAL_TENANT_ID


def _next_event_sequence(conn: sqlite3.Connection, run_id: str) -> int:
    row = conn.execute(
        "SELECT COALESCE(MAX(sequence), 0) + 1 AS next_sequence FROM events WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    return int(row["next_sequence"])


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


def _outbox_row_to_event(row: sqlite3.Row) -> AgentEvent:
    payload = json.loads(row["payload"])
    return AgentEvent(
        event_id=payload["event_id"],
        run_id=payload["run_id"],
        event_type=EventType(payload["event_type"]),
        payload=payload.get("payload") or {},
        sequence=int(payload["sequence"]),
        schema_version=payload.get("schema_version") or "1.0",
        created_at=payload["created_at"],
    )


def _seconds_ago(seconds: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat()

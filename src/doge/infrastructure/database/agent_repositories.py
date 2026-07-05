"""SQLite repositories for persisted agent runtime state."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from doge.config import get_settings
from doge.core.domain.agent_models import (
    AgentApproval,
    AgentArtifact,
    AgentEvent,
    AgentRun,
    AgentSession,
    AgentTurn,
    EventType,
    RunStatus,
    utc_now,
)
from doge.core.domain.enterprise_context import IdentitySnapshot
from doge.core.domain.model_policy import ModelPolicy
from doge.core.domain.run_execution_context import WorkflowRunContext
from doge.core.domain.document_models import Document, DocumentStatus
from doge.core.ports.agent_repository import (
    IApprovalRepository,
    IArtifactRepository,
    IDocumentRepository,
    IEventRepository,
    IRunRepository,
    ISessionRepository,
)
from doge.core.ports.idempotency_store import IIdempotencyStore
from doge.core.ports.worker_queue import IRunQueue
from doge.infrastructure.database.migration_runner import apply_context_migrations
from doge.infrastructure.database.sqlite import SQLiteConnection
from doge.infrastructure.database.tenant_guard import (
    LOCAL_TENANT_ID,
    guard_existing_tenant,
    resolve_tenant_id,
)
from doge.shared.scope import TenantScope


def _schema_path() -> Path:
    return Path(__file__).resolve().with_name("agent_schema.sql")


def bootstrap_agent_schema(db_path: Path | str | None = None) -> None:
    path = Path(db_path) if db_path is not None else get_settings().db.agent_db
    path.parent.mkdir(parents=True, exist_ok=True)
    sql = _schema_path().read_text(encoding="utf-8")
    with sqlite3.connect(str(path)) as conn:
        conn.executescript(sql)
        apply_context_migrations(conn)
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(name, applied_at) VALUES (?, ?)",
            ("agent_schema_v1", utc_now()),
        )
        conn.commit()


def _tenant_filter(column: str, tenant_id: str | None, *, prefix: str = " AND ") -> tuple[str, tuple[Any, ...]]:
    if tenant_id is None:
        return "", ()
    if tenant_id == LOCAL_TENANT_ID:
        return f"{prefix}({column} = ? OR {column} IS NULL)", (LOCAL_TENANT_ID,)
    return f"{prefix}{column} = ?", (tenant_id,)


def _tenant_id_from_scope(scope: TenantScope | str | None, tenant_id: str | None = None) -> str | None:
    if isinstance(scope, TenantScope):
        if tenant_id is not None and tenant_id != scope.tenant_id:
            raise ValueError(f"tenant mismatch for scope: {tenant_id} != {scope.tenant_id}")
        return scope.tenant_id
    if isinstance(scope, str):
        if tenant_id is not None and tenant_id != scope:
            raise ValueError(f"tenant mismatch for scope: {tenant_id} != {scope}")
        return scope
    return tenant_id


class _BaseAgentRepository:
    def __init__(self, db_path: Path | str | None = None) -> None:
        self._db_path = Path(db_path) if db_path is not None else get_settings().db.agent_db
        bootstrap_agent_schema(self._db_path)
        self._connection = SQLiteConnection(self._db_path, use_row_factory=True)

    def _connect(self):
        return self._connection.connect()


class SQLiteSessionRepository(_BaseAgentRepository, ISessionRepository):
    def save(
        self,
        session: AgentSession,
        scope: TenantScope | str | None = None,
        *,
        tenant_id: str | None = None,
    ) -> None:
        requested_tenant_id = _tenant_id_from_scope(scope, tenant_id)
        effective_tenant_id = resolve_tenant_id(session.tenant_id, requested_tenant_id)
        with self._connect() as conn:
            guard_existing_tenant(
                conn,
                table="sessions",
                key_column="session_id",
                key_value=session.session_id,
                tenant_id=effective_tenant_id,
            )
            conn.execute(
                """
                INSERT INTO sessions(session_id, tenant_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    tenant_id = excluded.tenant_id,
                    title = excluded.title,
                    updated_at = excluded.updated_at
                """,
                (session.session_id, effective_tenant_id, session.title, session.created_at, session.updated_at),
            )
            for turn in session.turns:
                turn_tenant_id = resolve_tenant_id(turn.tenant_id, effective_tenant_id)
                conn.execute(
                    """
                    INSERT INTO turns(turn_id, session_id, tenant_id, user_message, run_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(turn_id) DO NOTHING
                    """,
                    (
                        turn.turn_id,
                        turn.session_id,
                        turn_tenant_id,
                        turn.user_message,
                        turn.run_id,
                        turn.created_at,
                    ),
                )
            conn.commit()

    def get(
        self,
        session_id: str,
        scope: TenantScope | str | None = None,
        *,
        tenant_id: str | None = None,
    ) -> AgentSession | None:
        sql = "SELECT * FROM sessions WHERE session_id = ?"
        requested_tenant_id = _tenant_id_from_scope(scope, tenant_id)
        tenant_sql, tenant_params = _tenant_filter("tenant_id", requested_tenant_id)
        sql += tenant_sql
        params: tuple[Any, ...] = (session_id, *tenant_params)
        with self._connect() as conn:
            row = conn.execute(sql, params).fetchone()
            if row is None:
                return None
            return self._row_to_session(conn, row)

    def list_recent(
        self,
        scope: TenantScope | int | str | None = None,
        limit: int = 20,
        *,
        tenant_id: str | None = None,
    ) -> list[AgentSession]:
        if isinstance(scope, int):
            limit = scope
            scope = None
        requested_tenant_id = _tenant_id_from_scope(scope, tenant_id)
        sql = "SELECT * FROM sessions"
        tenant_sql, tenant_params = _tenant_filter("tenant_id", requested_tenant_id, prefix=" WHERE ")
        sql += tenant_sql
        sql += " ORDER BY updated_at DESC LIMIT ?"
        params: tuple[Any, ...] = (*tenant_params, limit)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_session(conn, row) for row in rows]

    def _row_to_session(self, conn: sqlite3.Connection, row: sqlite3.Row) -> AgentSession:
        turns = [
            AgentTurn(
                turn_id=item["turn_id"],
                session_id=item["session_id"],
                user_message=item["user_message"],
                run_id=item["run_id"],
                tenant_id=_row_value(item, "tenant_id"),
                created_at=item["created_at"],
            )
            for item in conn.execute(
                "SELECT * FROM turns WHERE session_id = ? ORDER BY created_at ASC",
                (row["session_id"],),
            ).fetchall()
        ]
        return AgentSession(
            session_id=row["session_id"],
            title=row["title"],
            tenant_id=_row_value(row, "tenant_id"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            turns=turns,
        )


class SQLiteRunRepository(_BaseAgentRepository, IRunRepository):
    def save(
        self,
        run: AgentRun,
        scope: TenantScope | str | None = None,
        *,
        tenant_id: str | None = None,
    ) -> None:
        requested_tenant_id = _tenant_id_from_scope(scope, tenant_id)
        effective_tenant_id = resolve_tenant_id(_tenant_id_from_run(run), requested_tenant_id)
        with self._connect() as conn:
            guard_existing_tenant(
                conn,
                table="runs",
                key_column="run_id",
                key_value=run.run_id,
                tenant_id=effective_tenant_id,
            )
            conn.execute(
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
                    effective_tenant_id,
                    run.session_id,
                    run.workflow,
                    run.question,
                    run.market,
                    run.language,
                    json.dumps(run.document_ids, ensure_ascii=False),
                    run.portfolio_id,
                    json.dumps(_model_policy_to_dict(run.model_policy), ensure_ascii=False),
                    _workflow_context_json(run.workflow_context),
                    _identity_snapshot_json(run.identity_snapshot),
                    run.status.value,
                    run.cancel_requested_at,
                    run.created_at,
                    run.updated_at,
                    run.schema_version,
                ),
            )
            conn.commit()

    def get(
        self,
        run_id: str,
        scope: TenantScope | str | None = None,
        *,
        tenant_id: str | None = None,
    ) -> AgentRun | None:
        return self._get(run_id, tenant_id=_tenant_id_from_scope(scope, tenant_id), hydrate_children=True)

    def get_run_header(
        self,
        run_id: str,
        scope: TenantScope | str | None = None,
        *,
        tenant_id: str | None = None,
    ) -> AgentRun | None:
        return self._get(run_id, tenant_id=_tenant_id_from_scope(scope, tenant_id), hydrate_children=False)

    def _get(self, run_id: str, *, tenant_id: str | None, hydrate_children: bool) -> AgentRun | None:
        sql = "SELECT * FROM runs WHERE run_id = ?"
        tenant_sql, tenant_params = _tenant_filter("tenant_id", tenant_id)
        sql += tenant_sql
        params: tuple[Any, ...] = (run_id, *tenant_params)
        with self._connect() as conn:
            row = conn.execute(sql, params).fetchone()
            if row is None:
                return None
            if hydrate_children:
                return _row_to_run(conn, row)
            return _row_to_run_header(row)

    def list_by_session(
        self,
        session_id: str,
        scope: TenantScope | str | None = None,
        *,
        tenant_id: str | None = None,
    ) -> list[AgentRun]:
        sql = "SELECT * FROM runs WHERE session_id = ?"
        tenant_sql, tenant_params = _tenant_filter("tenant_id", _tenant_id_from_scope(scope, tenant_id))
        sql += tenant_sql
        params: tuple[Any, ...] = (session_id, *tenant_params)
        sql += " ORDER BY created_at ASC"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [_row_to_run(conn, row) for row in rows]

    def list_recent(
        self,
        scope: TenantScope | int | str | None = None,
        limit: int = 20,
        *,
        tenant_id: str | None = None,
    ) -> list[AgentRun]:
        if isinstance(scope, int):
            limit = scope
            scope = None
        sql = "SELECT * FROM runs"
        tenant_sql, tenant_params = _tenant_filter("tenant_id", _tenant_id_from_scope(scope, tenant_id), prefix=" WHERE ")
        sql += tenant_sql
        sql += " ORDER BY updated_at DESC LIMIT ?"
        params: tuple[Any, ...] = (*tenant_params, limit)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [_row_to_run(conn, row) for row in rows]


class SQLiteEventRepository(_BaseAgentRepository, IEventRepository):
    def append(self, event: AgentEvent, tenant_id: str | None = None) -> AgentEvent:
        with self._connect() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                effective_tenant_id = resolve_tenant_id(_tenant_id_for_run(conn, event.run_id), tenant_id)
                if event.sequence <= 0:
                    event.sequence = _next_event_sequence(conn, event.run_id)
                conn.execute(
                    """
                    INSERT INTO events(
                        event_id, tenant_id, run_id, event_type, payload, sequence, schema_version, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.event_id,
                        effective_tenant_id,
                        event.run_id,
                        event.event_type.value,
                        json.dumps(event.payload, ensure_ascii=False),
                        event.sequence,
                        event.schema_version,
                        event.created_at,
                    ),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return event

    def list_for_run(self, run_id: str, after_sequence: int = 0, tenant_id: str | None = None) -> list[AgentEvent]:
        sql = """
                SELECT * FROM events
                WHERE run_id = ? AND sequence > ?
                """
        tenant_sql, tenant_params = _tenant_filter("tenant_id", tenant_id)
        sql += tenant_sql
        params: tuple[Any, ...] = (run_id, after_sequence, *tenant_params)
        sql += " ORDER BY sequence ASC"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [_row_to_event(row) for row in rows]


class SQLiteArtifactRepository(_BaseAgentRepository, IArtifactRepository):
    def save(self, artifact: AgentArtifact, tenant_id: str | None = None) -> None:
        with self._connect() as conn:
            effective_tenant_id = resolve_tenant_id(_tenant_id_for_run(conn, artifact.run_id), tenant_id)
            guard_existing_tenant(
                conn,
                table="artifacts",
                key_column="artifact_id",
                key_value=artifact.artifact_id,
                tenant_id=effective_tenant_id,
            )
            conn.execute(
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
                    effective_tenant_id,
                    artifact.run_id,
                    artifact.kind,
                    artifact.title,
                    artifact.content,
                    json.dumps(artifact.data, ensure_ascii=False),
                    artifact.created_at,
                ),
            )
            conn.commit()

    def list_for_run(self, run_id: str, tenant_id: str | None = None) -> list[AgentArtifact]:
        sql = "SELECT * FROM artifacts WHERE run_id = ?"
        tenant_sql, tenant_params = _tenant_filter("tenant_id", tenant_id)
        sql += tenant_sql
        params: tuple[Any, ...] = (run_id, *tenant_params)
        sql += " ORDER BY created_at ASC"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [_row_to_artifact(row) for row in rows]


class SQLiteApprovalRepository(_BaseAgentRepository, IApprovalRepository):
    def save(self, approval: AgentApproval, tenant_id: str | None = None) -> None:
        with self._connect() as conn:
            effective_tenant_id = resolve_tenant_id(_tenant_id_for_run(conn, approval.run_id), tenant_id)
            guard_existing_tenant(
                conn,
                table="approvals",
                key_column="approval_id",
                key_value=approval.approval_id,
                tenant_id=effective_tenant_id,
            )
            conn.execute(
                """
                INSERT INTO approvals(
                    approval_id,
                    tenant_id,
                    run_id,
                    action,
                    risk_level,
                    status,
                    created_at,
                    resolved_at,
                    why_needed,
                    impact,
                    deny_consequence,
                    publish_target
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(approval_id) DO UPDATE SET
                    tenant_id = excluded.tenant_id,
                    run_id = excluded.run_id,
                    action = excluded.action,
                    risk_level = excluded.risk_level,
                    status = excluded.status,
                    resolved_at = excluded.resolved_at,
                    why_needed = excluded.why_needed,
                    impact = excluded.impact,
                    deny_consequence = excluded.deny_consequence,
                    publish_target = excluded.publish_target
                """,
                (
                    approval.approval_id,
                    effective_tenant_id,
                    approval.run_id,
                    approval.action,
                    approval.risk_level,
                    approval.status,
                    approval.created_at,
                    approval.resolved_at,
                    approval.why_needed,
                    approval.impact,
                    approval.deny_consequence,
                    approval.publish_target,
                ),
            )
            conn.commit()

    def get(self, approval_id: str, tenant_id: str | None = None) -> AgentApproval | None:
        sql = "SELECT * FROM approvals WHERE approval_id = ?"
        tenant_sql, tenant_params = _tenant_filter("tenant_id", tenant_id)
        sql += tenant_sql
        params: tuple[Any, ...] = (approval_id, *tenant_params)
        with self._connect() as conn:
            row = conn.execute(sql, params).fetchone()
            return _row_to_approval(row) if row else None

    def list_for_run(self, run_id: str, tenant_id: str | None = None) -> list[AgentApproval]:
        sql = "SELECT * FROM approvals WHERE run_id = ?"
        tenant_sql, tenant_params = _tenant_filter("tenant_id", tenant_id)
        sql += tenant_sql
        params: tuple[Any, ...] = (run_id, *tenant_params)
        sql += " ORDER BY created_at ASC"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [_row_to_approval(row) for row in rows]


class SQLiteDocumentRepository(_BaseAgentRepository, IDocumentRepository):
    def save(
        self,
        document: Document | dict[str, Any],
        scope: TenantScope | str | None = None,
        *,
        tenant_id: str | None = None,
    ) -> None:
        requested_tenant_id = _tenant_id_from_scope(scope, tenant_id)
        record = _document_to_record(document)
        record["tenant_id"] = resolve_tenant_id(record.get("tenant_id"), requested_tenant_id)
        with self._connect() as conn:
            guard_existing_tenant(
                conn,
                table="documents",
                key_column="document_id",
                key_value=record["document_id"],
                tenant_id=record["tenant_id"],
            )
            conn.execute(
                """
                INSERT INTO documents(
                    document_id, tenant_id, filename, original_filename, content,
                    file_hash, mime_type, size_bytes, storage_path, kimi_file_id,
                    kimi_file_purpose, parsing_status, parser_error, status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(document_id) DO UPDATE SET
                    tenant_id = excluded.tenant_id,
                    filename = excluded.filename,
                    original_filename = excluded.original_filename,
                    content = excluded.content,
                    file_hash = excluded.file_hash,
                    mime_type = excluded.mime_type,
                    size_bytes = excluded.size_bytes,
                    storage_path = excluded.storage_path,
                    kimi_file_id = excluded.kimi_file_id,
                    kimi_file_purpose = excluded.kimi_file_purpose,
                    parsing_status = excluded.parsing_status,
                    parser_error = excluded.parser_error,
                    status = excluded.status,
                    updated_at = excluded.updated_at
                """,
                (
                    record["document_id"],
                    record.get("tenant_id"),
                    record["filename"],
                    record["original_filename"],
                    record.get("content"),
                    record.get("file_hash"),
                    record.get("mime_type"),
                    record.get("size_bytes"),
                    record.get("storage_path"),
                    record.get("kimi_file_id"),
                    record.get("kimi_file_purpose"),
                    record["parsing_status"],
                    record.get("parser_error"),
                    record["status"],
                    record["created_at"],
                    record["updated_at"],
                ),
            )
            conn.commit()

    def get(
        self,
        document_id: str,
        scope: TenantScope | str | None = None,
        *,
        tenant_id: str | None = None,
    ) -> dict[str, Any] | None:
        sql = "SELECT * FROM documents WHERE document_id = ?"
        requested_tenant_id = _tenant_id_from_scope(scope, tenant_id)
        tenant_sql, tenant_params = _tenant_filter("tenant_id", requested_tenant_id)
        sql += tenant_sql
        params: tuple[Any, ...] = (document_id, *tenant_params)
        with self._connect() as conn:
            row = conn.execute(sql, params).fetchone()
            return _row_to_document_dict(row) if row else None

    def get_by_hash(
        self,
        file_hash: str,
        scope: TenantScope | str | None = None,
        *,
        tenant_id: str | None = None,
    ) -> dict[str, Any] | None:
        sql = "SELECT * FROM documents WHERE file_hash = ?"
        requested_tenant_id = _tenant_id_from_scope(scope, tenant_id)
        tenant_sql, tenant_params = _tenant_filter("tenant_id", requested_tenant_id)
        sql += tenant_sql
        params: tuple[Any, ...] = (file_hash, *tenant_params)
        sql += " ORDER BY created_at DESC LIMIT 1"
        with self._connect() as conn:
            row = conn.execute(sql, params).fetchone()
            return _row_to_document_dict(row) if row else None

    def list_recent(
        self,
        scope: TenantScope | int | str | None = None,
        limit: int = 100,
        *,
        tenant_id: str | None = None,
    ) -> list[dict[str, Any]]:
        if isinstance(scope, int):
            limit = scope
            scope = None
        requested_tenant_id = _tenant_id_from_scope(scope, tenant_id)
        sql = "SELECT * FROM documents"
        tenant_sql, tenant_params = _tenant_filter("tenant_id", requested_tenant_id, prefix=" WHERE ")
        sql += tenant_sql
        sql += " ORDER BY created_at DESC LIMIT ?"
        params: tuple[Any, ...] = (*tenant_params, limit)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [_row_to_document_dict(row) for row in rows]


class SQLiteRunQueue(_BaseAgentRepository, IRunQueue):
    def enqueue(self, run_id: str) -> None:
        self.append_status(run_id, "queued")

    def dequeue(self) -> str | None:
        return self.claim_atomic("legacy-worker", lease_seconds=30)

    def claim_atomic(self, worker_id: str, lease_seconds: int, max_attempts: int = 3) -> str | None:
        now = utc_now()
        lease_expires_at = _seconds_from_now(lease_seconds)
        with self._connect() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                row = conn.execute(
                    """
                    SELECT q.*
                    FROM run_queue q
                    JOIN (
                        SELECT run_id, MAX(queue_id) AS max_queue_id
                        FROM run_queue
                        GROUP BY run_id
                    ) latest
                    ON q.run_id = latest.run_id AND q.queue_id = latest.max_queue_id
                    WHERE q.status = 'queued'
                       OR (q.status = 'running' AND (q.lease_expires_at IS NULL OR q.lease_expires_at <= ?))
                    ORDER BY q.queue_id ASC
                    LIMIT 1
                    """,
                    (now,),
                ).fetchone()
                if row is None:
                    conn.commit()
                    return None
                attempt_count = int(_row_value(row, "attempt_count") or 0) + 1
                if attempt_count > max_attempts:
                    conn.execute(
                        """
                        INSERT INTO run_queue(
                            run_id, status, attempt_count, created_at, updated_at
                        )
                        VALUES (?, 'dead_letter', ?, ?, ?)
                        """,
                        (row["run_id"], int(_row_value(row, "attempt_count") or 0), now, now),
                    )
                    conn.commit()
                    return None
                conn.execute(
                    """
                    INSERT INTO run_queue(
                        run_id, status, worker_id, leased_at, lease_expires_at,
                        attempt_count, created_at, updated_at
                    )
                    VALUES (?, 'running', ?, ?, ?, ?, ?, ?)
                    """,
                    (row["run_id"], worker_id, now, lease_expires_at, attempt_count, now, now),
                )
                conn.commit()
                return row["run_id"]
            except Exception:
                conn.rollback()
                raise

    def heartbeat(self, worker_id: str, run_id: str, lease_seconds: int) -> None:
        now = utc_now()
        lease_expires_at = _seconds_from_now(lease_seconds)
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE run_queue
                SET leased_at = ?, lease_expires_at = ?, updated_at = ?
                WHERE queue_id = (
                    SELECT queue_id FROM run_queue
                    WHERE run_id = ?
                    ORDER BY queue_id DESC
                    LIMIT 1
                )
                AND run_id = ?
                AND status = 'running'
                AND worker_id = ?
                """,
                (now, lease_expires_at, now, run_id, run_id, worker_id),
            )
            conn.commit()

    def release_claim(self, run_id: str, worker_id: str, final_status: str) -> None:
        now = utc_now()
        with self._connect() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                row = conn.execute(
                    """
                    SELECT * FROM run_queue
                    WHERE run_id = ?
                    ORDER BY queue_id DESC
                    LIMIT 1
                    """,
                    (run_id,),
                ).fetchone()
                if row is None or row["status"] != "running" or row["worker_id"] != worker_id:
                    conn.commit()
                    return
                conn.execute(
                    """
                    INSERT INTO run_queue(
                        run_id, status, worker_id, attempt_count, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (run_id, final_status, worker_id, int(row["attempt_count"] or 0), now, now),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def recover_stalled_leases(self, lease_timeout_seconds: int, max_attempts: int = 3) -> list[str]:
        now = utc_now()
        stale_before = _seconds_ago(lease_timeout_seconds)
        recovered: list[str] = []
        with self._connect() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                rows = conn.execute(
                    """
                    SELECT q.*
                    FROM run_queue q
                    JOIN (
                        SELECT run_id, MAX(queue_id) AS max_queue_id
                        FROM run_queue
                        GROUP BY run_id
                    ) latest
                    ON q.run_id = latest.run_id AND q.queue_id = latest.max_queue_id
                    WHERE q.status = 'running'
                      AND (
                        q.lease_expires_at IS NULL
                        OR q.lease_expires_at <= ?
                        OR q.leased_at <= ?
                      )
                    ORDER BY q.queue_id ASC
                    """,
                    (now, stale_before),
                ).fetchall()
                for row in rows:
                    attempt_count = int(row["attempt_count"] or 0)
                    if attempt_count >= max_attempts:
                        conn.execute(
                            """
                            INSERT INTO run_queue(
                                run_id, status, attempt_count, created_at, updated_at
                            )
                            VALUES (?, 'dead_letter', ?, ?, ?)
                            """,
                            (row["run_id"], attempt_count, now, now),
                        )
                        continue
                    recovered.append(row["run_id"])
                    conn.execute(
                        """
                        INSERT INTO run_queue(
                            run_id, status, attempt_count, created_at, updated_at
                        )
                        VALUES (?, 'queued', ?, ?, ?)
                        """,
                        (row["run_id"], attempt_count, now, now),
                    )
                conn.commit()
                return recovered
            except Exception:
                conn.rollback()
                raise

    def list_pending(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT q.run_id
                FROM run_queue q
                JOIN (
                    SELECT run_id, MAX(queue_id) AS max_queue_id
                    FROM run_queue
                    GROUP BY run_id
                ) latest
                ON q.run_id = latest.run_id AND q.queue_id = latest.max_queue_id
                WHERE q.status = 'queued'
                ORDER BY q.queue_id ASC
                """
            ).fetchall()
            return [row["run_id"] for row in rows]

    def append_status(self, run_id: str, status: str) -> None:
        now = utc_now()
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT attempt_count FROM run_queue
                WHERE run_id = ?
                ORDER BY queue_id DESC
                LIMIT 1
                """,
                (run_id,),
            ).fetchone()
            attempt_count = int(row["attempt_count"] or 0) if row else 0
            conn.execute(
                """
                INSERT INTO run_queue(run_id, status, attempt_count, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (run_id, status, attempt_count, now, now),
            )
            conn.commit()

    def is_ready(self) -> bool:
        try:
            with self._connect() as conn:
                conn.execute("SELECT 1 FROM run_queue LIMIT 1")
            return True
        except Exception:
            return False


class SQLiteIdempotencyStore(_BaseAgentRepository, IIdempotencyStore):
    def get(self, key: str, scope: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT run_id FROM idempotency_keys WHERE key = ? AND scope = ?",
                (key, scope),
            ).fetchone()
            return row["run_id"] if row else None

    def set(self, key: str, scope: str, run_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO idempotency_keys(key, scope, run_id, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (key, scope, run_id, utc_now()),
            )
            conn.commit()


def _row_to_run(conn: sqlite3.Connection, row: sqlite3.Row) -> AgentRun:
    tenant_id = _row_value(row, "tenant_id")
    run = _row_to_run_header(row)
    child_clause = "run_id = ?"
    child_params: tuple[Any, ...] = (run.run_id,)
    if tenant_id is not None:
        child_clause += " AND tenant_id = ?"
        child_params = (run.run_id, tenant_id)
    run.events = [
        _row_to_event(item)
        for item in conn.execute(
            f"SELECT * FROM events WHERE {child_clause} ORDER BY sequence ASC",
            child_params,
        ).fetchall()
    ]
    run.artifacts = [
        _row_to_artifact(item)
        for item in conn.execute(
            f"SELECT * FROM artifacts WHERE {child_clause} ORDER BY created_at ASC",
            child_params,
        ).fetchall()
    ]
    run.approvals = [
        _row_to_approval(item)
        for item in conn.execute(
            f"SELECT * FROM approvals WHERE {child_clause} ORDER BY created_at ASC",
            child_params,
        ).fetchall()
    ]
    return run


def _row_to_run_header(row: sqlite3.Row) -> AgentRun:
    policy_payload = json.loads(row["model_policy"] or "{}")
    return AgentRun(
        run_id=row["run_id"],
        workflow=row["workflow"],
        question=row["question"],
        session_id=row["session_id"],
        market=row["market"],
        language=row["language"],
        document_ids=json.loads(row["document_ids"] or "[]"),
        portfolio_id=row["portfolio_id"],
        model_policy=ModelPolicy.from_dict(policy_payload),
        workflow_context=_workflow_context_from_row(row),
        identity_snapshot=_identity_snapshot_from_row(row, policy_payload),
        status=RunStatus(row["status"]),
        cancel_requested_at=row["cancel_requested_at"],
        schema_version=row["schema_version"] or "1.0",
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_value(row: sqlite3.Row, key: str) -> Any:
    return row[key] if key in row.keys() else None


def _tenant_id_from_run(run: AgentRun) -> str | None:
    if run.identity_snapshot is not None:
        return run.identity_snapshot.tenant_id
    return None


def _tenant_id_for_run(conn: sqlite3.Connection, run_id: str) -> str | None:
    row = conn.execute("SELECT tenant_id, model_policy, identity_snapshot FROM runs WHERE run_id = ?", (run_id,)).fetchone()
    if row is None:
        return None
    tenant_id = _row_value(row, "tenant_id")
    if tenant_id:
        return str(tenant_id)
    try:
        policy_payload = json.loads(row["model_policy"] or "{}")
    except Exception:
        policy_payload = {}
    identity_snapshot = _identity_snapshot_from_row(row, policy_payload)
    if identity_snapshot is not None:
        return identity_snapshot.tenant_id
    legacy = IdentitySnapshot.from_mapping(policy_payload)
    return legacy.tenant_id if legacy is not None else None


def _next_event_sequence(conn: sqlite3.Connection, run_id: str) -> int:
    row = conn.execute(
        "SELECT COALESCE(MAX(sequence), 0) + 1 AS next_sequence FROM events WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    return int(row["next_sequence"])


def _seconds_from_now(seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()


def _seconds_ago(seconds: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat()


def _row_to_event(row: sqlite3.Row) -> AgentEvent:
    return AgentEvent(
        event_id=row["event_id"],
        run_id=row["run_id"],
        event_type=EventType(row["event_type"]),
        payload=json.loads(row["payload"] or "{}"),
        sequence=int(row["sequence"]),
        schema_version=row["schema_version"] or "1.0",
        created_at=row["created_at"],
    )


def _row_to_artifact(row: sqlite3.Row) -> AgentArtifact:
    return AgentArtifact(
        artifact_id=row["artifact_id"],
        run_id=row["run_id"],
        kind=row["kind"],
        title=row["title"],
        content=row["content"],
        data=json.loads(row["data"] or "{}"),
        created_at=row["created_at"],
    )


def _row_to_approval(row: sqlite3.Row) -> AgentApproval:
    return AgentApproval(
        approval_id=row["approval_id"],
        run_id=row["run_id"],
        action=row["action"],
        risk_level=row["risk_level"],
        status=row["status"],
        created_at=row["created_at"],
        resolved_at=row["resolved_at"],
        why_needed=row["why_needed"],
        impact=row["impact"],
        deny_consequence=row["deny_consequence"],
        publish_target=row["publish_target"],
    )


def _model_policy_to_dict(policy: Any) -> dict[str, Any]:
    return ModelPolicy.from_dict(policy).to_dict()


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
    return json.dumps(payload, ensure_ascii=False)


def _workflow_context_from_row(row: sqlite3.Row) -> WorkflowRunContext | None:
    raw = _row_value(row, "workflow_context")
    if not raw:
        return None
    try:
        return WorkflowRunContext.from_mapping(json.loads(raw))
    except (TypeError, json.JSONDecodeError):
        return None


def _identity_snapshot_json(snapshot: IdentitySnapshot | dict[str, Any] | None) -> str | None:
    normalized = IdentitySnapshot.from_mapping(snapshot)
    if normalized is None:
        return None
    return json.dumps(normalized.to_dict(), ensure_ascii=False)


def _identity_snapshot_from_row(row: sqlite3.Row, policy_payload: dict[str, Any]) -> IdentitySnapshot | None:
    raw = _row_value(row, "identity_snapshot")
    if raw:
        try:
            return IdentitySnapshot.from_mapping(json.loads(raw))
        except Exception:
            return None
    return IdentitySnapshot.from_mapping(policy_payload)


def _document_to_record(document: Document | dict[str, Any]) -> dict[str, Any]:
    if isinstance(document, Document):
        data = document.to_dict()
    else:
        data = dict(document)
    status = _normalize_document_status(data.get("parsing_status") or data.get("status"))
    now = utc_now()
    filename = data.get("original_filename") or data.get("filename") or data["document_id"]
    return {
        "document_id": data["document_id"],
        "tenant_id": data.get("tenant_id"),
        "filename": data.get("filename") or filename,
        "original_filename": filename,
        "content": data.get("content") or data.get("parsed_content"),
        "file_hash": data.get("file_hash"),
        "mime_type": data.get("mime_type"),
        "size_bytes": data.get("size_bytes") or data.get("file_size_bytes"),
        "storage_path": data.get("storage_path"),
        "kimi_file_id": data.get("kimi_file_id"),
        "kimi_file_purpose": data.get("kimi_file_purpose"),
        "parsing_status": status.value,
        "parser_error": data.get("parser_error") or data.get("error_message"),
        "status": status.value,
        "created_at": data.get("created_at") or now,
        "updated_at": data.get("updated_at") or now,
    }


def _row_to_document_dict(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    status = _normalize_document_status(data.get("parsing_status") or data.get("status"))
    original_filename = data.get("original_filename") or data.get("filename") or data["document_id"]
    return {
        **data,
        "filename": data.get("filename") or original_filename,
        "original_filename": original_filename,
        "parsing_status": status.value,
        "status": status.value,
        "size_bytes": data.get("size_bytes"),
        "kimi_file_purpose": data.get("kimi_file_purpose"),
        "parser_error": data.get("parser_error"),
        "updated_at": data.get("updated_at") or data.get("created_at"),
    }


def _normalize_document_status(value: str | None) -> DocumentStatus:
    if value == "ready":
        return DocumentStatus.PARSED
    if not value:
        return DocumentStatus.REGISTERED
    return DocumentStatus(value)

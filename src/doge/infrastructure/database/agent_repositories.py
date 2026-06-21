"""SQLite repositories for persisted agent runtime state."""

from __future__ import annotations

import json
import sqlite3
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
from doge.core.domain.model_policy import ModelPolicy
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
from doge.infrastructure.database.sqlite import SQLiteConnection


def _schema_path() -> Path:
    return Path(__file__).resolve().with_name("agent_schema.sql")


def bootstrap_agent_schema(db_path: Path | str | None = None) -> None:
    path = Path(db_path) if db_path is not None else get_settings().db.agent_db
    path.parent.mkdir(parents=True, exist_ok=True)
    sql = _schema_path().read_text(encoding="utf-8")
    with sqlite3.connect(str(path)) as conn:
        conn.executescript(sql)
        _migrate_idempotency_key_scope(conn)
        _migrate_documents_metadata(conn)
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(name, applied_at) VALUES (?, ?)",
            ("agent_schema_v1", utc_now()),
        )
        conn.commit()


def _migrate_idempotency_key_scope(conn: sqlite3.Connection) -> None:
    columns = conn.execute("PRAGMA table_info(idempotency_keys)").fetchall()
    pk_columns = [row[1] for row in columns if row[5]]
    if pk_columns in (["key", "scope"], ["scope", "key"]):
        return
    conn.execute("ALTER TABLE idempotency_keys RENAME TO idempotency_keys_legacy")
    conn.execute(
        """
        CREATE TABLE idempotency_keys (
            key TEXT NOT NULL,
            scope TEXT NOT NULL,
            run_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY(key, scope)
        )
        """
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO idempotency_keys(key, scope, run_id, created_at)
        SELECT key, scope, run_id, created_at FROM idempotency_keys_legacy
        """
    )
    conn.execute("DROP TABLE idempotency_keys_legacy")


def _migrate_documents_metadata(conn: sqlite3.Connection) -> None:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(documents)").fetchall()}
    additions = {
        "original_filename": "TEXT",
        "file_hash": "TEXT",
        "mime_type": "TEXT",
        "size_bytes": "INTEGER",
        "storage_path": "TEXT",
        "kimi_file_id": "TEXT",
        "kimi_file_purpose": "TEXT",
        "parsing_status": "TEXT NOT NULL DEFAULT 'registered'",
        "parser_error": "TEXT",
        "updated_at": "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
    }
    for column, ddl in additions.items():
        if column not in columns:
            conn.execute(f"ALTER TABLE documents ADD COLUMN {column} {ddl}")
    conn.execute(
        """
        UPDATE documents
        SET original_filename = COALESCE(original_filename, filename),
            parsing_status = CASE
                WHEN parsing_status IS NULL OR parsing_status = '' THEN
                    CASE WHEN status = 'ready' THEN 'parsed' ELSE COALESCE(status, 'registered') END
                ELSE parsing_status
            END,
            status = CASE
                WHEN status = 'ready' THEN 'parsed'
                ELSE COALESCE(status, parsing_status, 'registered')
            END,
            updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP)
        """
    )


class _BaseAgentRepository:
    def __init__(self, db_path: Path | str | None = None) -> None:
        self._db_path = Path(db_path) if db_path is not None else get_settings().db.agent_db
        bootstrap_agent_schema(self._db_path)
        self._connection = SQLiteConnection(self._db_path, use_row_factory=True)

    def _connect(self):
        return self._connection.connect()


class SQLiteSessionRepository(_BaseAgentRepository, ISessionRepository):
    def save(self, session: AgentSession) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sessions(session_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    title = excluded.title,
                    updated_at = excluded.updated_at
                """,
                (session.session_id, session.title, session.created_at, session.updated_at),
            )
            conn.execute("DELETE FROM turns WHERE session_id = ?", (session.session_id,))
            for turn in session.turns:
                conn.execute(
                    """
                    INSERT INTO turns(turn_id, session_id, user_message, run_id, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (turn.turn_id, turn.session_id, turn.user_message, turn.run_id, turn.created_at),
                )
            conn.commit()

    def get(self, session_id: str) -> AgentSession | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
            if row is None:
                return None
            return self._row_to_session(conn, row)

    def list_recent(self, limit: int = 20) -> list[AgentSession]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [self._row_to_session(conn, row) for row in rows]

    def _row_to_session(self, conn: sqlite3.Connection, row: sqlite3.Row) -> AgentSession:
        turns = [
            AgentTurn(
                turn_id=item["turn_id"],
                session_id=item["session_id"],
                user_message=item["user_message"],
                run_id=item["run_id"],
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
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            turns=turns,
        )


class SQLiteRunRepository(_BaseAgentRepository, IRunRepository):
    def save(self, run: AgentRun) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO runs(
                    run_id, session_id, workflow, question, market, language,
                    document_ids, portfolio_id, model_policy, status,
                    cancel_requested_at, created_at, updated_at, schema_version
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    session_id = excluded.session_id,
                    workflow = excluded.workflow,
                    question = excluded.question,
                    market = excluded.market,
                    language = excluded.language,
                    document_ids = excluded.document_ids,
                    portfolio_id = excluded.portfolio_id,
                    model_policy = excluded.model_policy,
                    status = excluded.status,
                    cancel_requested_at = excluded.cancel_requested_at,
                    updated_at = excluded.updated_at,
                    schema_version = excluded.schema_version
                """,
                (
                    run.run_id,
                    run.session_id,
                    run.workflow,
                    run.question,
                    run.market,
                    run.language,
                    json.dumps(run.document_ids, ensure_ascii=False),
                    run.portfolio_id,
                    json.dumps(_model_policy_to_dict(run.model_policy), ensure_ascii=False),
                    run.status.value,
                    run.cancel_requested_at,
                    run.created_at,
                    run.updated_at,
                    run.schema_version,
                ),
            )
            conn.commit()

    def get(self, run_id: str) -> AgentRun | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
            if row is None:
                return None
            return _row_to_run(conn, row)

    def list_by_session(self, session_id: str) -> list[AgentRun]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM runs WHERE session_id = ? ORDER BY created_at ASC",
                (session_id,),
            ).fetchall()
            return [_row_to_run(conn, row) for row in rows]

    def list_recent(self, limit: int = 20) -> list[AgentRun]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM runs ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [_row_to_run(conn, row) for row in rows]


class SQLiteEventRepository(_BaseAgentRepository, IEventRepository):
    def append(self, event: AgentEvent) -> AgentEvent:
        with self._connect() as conn:
            if event.sequence <= 0:
                row = conn.execute(
                    "SELECT COALESCE(MAX(sequence), 0) + 1 AS next_sequence FROM events WHERE run_id = ?",
                    (event.run_id,),
                ).fetchone()
                event.sequence = int(row["next_sequence"])
            conn.execute(
                """
                INSERT OR REPLACE INTO events(
                    event_id, run_id, event_type, payload, sequence, schema_version, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.run_id,
                    event.event_type.value,
                    json.dumps(event.payload, ensure_ascii=False),
                    event.sequence,
                    event.schema_version,
                    event.created_at,
                ),
            )
            conn.commit()
        return event

    def list_for_run(self, run_id: str, after_sequence: int = 0) -> list[AgentEvent]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM events
                WHERE run_id = ? AND sequence > ?
                ORDER BY sequence ASC
                """,
                (run_id, after_sequence),
            ).fetchall()
            return [_row_to_event(row) for row in rows]


class SQLiteArtifactRepository(_BaseAgentRepository, IArtifactRepository):
    def save(self, artifact: AgentArtifact) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO artifacts(artifact_id, run_id, kind, title, content, data, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(artifact_id) DO UPDATE SET
                    run_id = excluded.run_id,
                    kind = excluded.kind,
                    title = excluded.title,
                    content = excluded.content,
                    data = excluded.data
                """,
                (
                    artifact.artifact_id,
                    artifact.run_id,
                    artifact.kind,
                    artifact.title,
                    artifact.content,
                    json.dumps(artifact.data, ensure_ascii=False),
                    artifact.created_at,
                ),
            )
            conn.commit()

    def list_for_run(self, run_id: str) -> list[AgentArtifact]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM artifacts WHERE run_id = ? ORDER BY created_at ASC",
                (run_id,),
            ).fetchall()
            return [_row_to_artifact(row) for row in rows]


class SQLiteApprovalRepository(_BaseAgentRepository, IApprovalRepository):
    def save(self, approval: AgentApproval) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO approvals(approval_id, run_id, action, risk_level, status, created_at, resolved_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(approval_id) DO UPDATE SET
                    run_id = excluded.run_id,
                    action = excluded.action,
                    risk_level = excluded.risk_level,
                    status = excluded.status,
                    resolved_at = excluded.resolved_at
                """,
                (
                    approval.approval_id,
                    approval.run_id,
                    approval.action,
                    approval.risk_level,
                    approval.status,
                    approval.created_at,
                    approval.resolved_at,
                ),
            )
            conn.commit()

    def get(self, approval_id: str) -> AgentApproval | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM approvals WHERE approval_id = ?", (approval_id,)).fetchone()
            return _row_to_approval(row) if row else None

    def list_for_run(self, run_id: str) -> list[AgentApproval]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM approvals WHERE run_id = ? ORDER BY created_at ASC",
                (run_id,),
            ).fetchall()
            return [_row_to_approval(row) for row in rows]


class SQLiteDocumentRepository(_BaseAgentRepository, IDocumentRepository):
    def save(self, document: Document | dict[str, Any]) -> None:
        record = _document_to_record(document)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO documents(
                    document_id, filename, original_filename, content,
                    file_hash, mime_type, size_bytes, storage_path, kimi_file_id,
                    kimi_file_purpose, parsing_status, parser_error, status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(document_id) DO UPDATE SET
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

    def get(self, document_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM documents WHERE document_id = ?", (document_id,)).fetchone()
            return _row_to_document_dict(row) if row else None

    def get_by_hash(self, file_hash: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM documents WHERE file_hash = ? ORDER BY created_at DESC LIMIT 1",
                (file_hash,),
            ).fetchone()
            return _row_to_document_dict(row) if row else None

    def list_recent(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM documents ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [_row_to_document_dict(row) for row in rows]


class SQLiteRunQueue(_BaseAgentRepository, IRunQueue):
    def enqueue(self, run_id: str) -> None:
        self.append_status(run_id, "queued")

    def dequeue(self) -> str | None:
        pending = self.list_pending()
        if not pending:
            return None
        run_id = pending[0]
        self.append_status(run_id, "running")
        return run_id

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
                WHERE q.status IN ('queued', 'running')
                ORDER BY q.queue_id ASC
                """
            ).fetchall()
            return [row["run_id"] for row in rows]

    def append_status(self, run_id: str, status: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO run_queue(run_id, status, created_at, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                (run_id, status),
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
    run = AgentRun(
        run_id=row["run_id"],
        workflow=row["workflow"],
        question=row["question"],
        session_id=row["session_id"],
        market=row["market"],
        language=row["language"],
        document_ids=json.loads(row["document_ids"] or "[]"),
        portfolio_id=row["portfolio_id"],
        model_policy=ModelPolicy.from_dict(json.loads(row["model_policy"] or "{}")),
        status=RunStatus(row["status"]),
        cancel_requested_at=row["cancel_requested_at"],
        schema_version=row["schema_version"] or "1.0",
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
    run.events = [
        _row_to_event(item)
        for item in conn.execute(
            "SELECT * FROM events WHERE run_id = ? ORDER BY sequence ASC",
            (run.run_id,),
        ).fetchall()
    ]
    run.artifacts = [
        _row_to_artifact(item)
        for item in conn.execute(
            "SELECT * FROM artifacts WHERE run_id = ? ORDER BY created_at ASC",
            (run.run_id,),
        ).fetchall()
    ]
    run.approvals = [
        _row_to_approval(item)
        for item in conn.execute(
            "SELECT * FROM approvals WHERE run_id = ? ORDER BY created_at ASC",
            (run.run_id,),
        ).fetchall()
    ]
    return run


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
    )


def _model_policy_to_dict(policy: Any) -> dict[str, Any]:
    return ModelPolicy.from_dict(policy).to_dict()


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

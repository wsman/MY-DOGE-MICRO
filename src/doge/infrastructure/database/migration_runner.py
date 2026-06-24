"""Context-owned SQLite migration runner."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Callable, Iterable

from doge.core.domain.agent_models import utc_now
from doge.infrastructure.database.tenant_guard import LOCAL_TENANT_ID


MigrationFn = Callable[[sqlite3.Connection], None]


@dataclass(frozen=True)
class Migration:
    """One idempotent SQLite migration owned by a bounded context."""

    context: str
    name: str
    apply: MigrationFn

    @property
    def key(self) -> str:
        return f"{self.context}:{self.name}"


def apply_context_migrations(
    conn: sqlite3.Connection,
    *,
    contexts: Iterable[str] | None = None,
) -> list[str]:
    """Apply registered context migrations and record them idempotently."""

    _ensure_migration_table(conn)
    allowed = set(contexts) if contexts is not None else None
    applied: list[str] = []
    for migration in _migrations():
        if allowed is not None and migration.context not in allowed:
            continue
        if _is_applied(conn, migration.key):
            continue
        migration.apply(conn)
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(name, applied_at) VALUES (?, ?)",
            (migration.key, utc_now()),
        )
        applied.append(migration.key)
    return applied


def registered_migrations() -> tuple[Migration, ...]:
    """Return registered migrations for tests and diagnostics."""

    return _migrations()


def _migrations() -> tuple[Migration, ...]:
    return (
        Migration("runtime", "idempotency_key_scope", _migrate_idempotency_key_scope),
        Migration("evidence", "documents_metadata", _migrate_documents_metadata),
        Migration("runtime", "tenant_partition_columns", _migrate_tenant_partition_columns),
        Migration("runtime", "local_tenant_backfill", _migrate_runtime_local_tenant_backfill),
        Migration("evidence", "local_tenant_backfill", _migrate_evidence_local_tenant_backfill),
        Migration("portfolio", "local_tenant_backfill", _migrate_portfolio_local_tenant_backfill),
        Migration("workspace", "local_tenant_backfill", _migrate_workspace_local_tenant_backfill),
        Migration("runtime", "run_identity_snapshot", _migrate_run_identity_snapshot),
        Migration("runtime", "run_workflow_context", _migrate_run_workflow_context),
        Migration("runtime", "runtime_outbox", _migrate_runtime_outbox),
        Migration("runtime", "run_queue_leases", _migrate_run_queue_leases),
    )


def _ensure_migration_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            name TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def _is_applied(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute("SELECT 1 FROM schema_migrations WHERE name = ?", (name,)).fetchone()
    return row is not None


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


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
    columns = _columns(conn, "documents")
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
        "updated_at": "TEXT",
    }
    for column, ddl in additions.items():
        if column not in columns:
            conn.execute(f"ALTER TABLE documents ADD COLUMN {column} {ddl}")
    conn.execute(
        """
        UPDATE documents
        SET original_filename = COALESCE(original_filename, filename),
            parsing_status = CASE
                WHEN status = 'ready'
                    AND (parsing_status IS NULL OR parsing_status = '' OR parsing_status = 'registered')
                    THEN 'parsed'
                WHEN parsing_status IS NULL OR parsing_status = '' THEN COALESCE(status, 'registered')
                ELSE parsing_status
            END,
            status = CASE
                WHEN status = 'ready' THEN 'parsed'
                ELSE COALESCE(status, parsing_status, 'registered')
            END,
            updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP)
        """
    )


def _migrate_tenant_partition_columns(conn: sqlite3.Connection) -> None:
    for table in (
        "sessions",
        "turns",
        "runs",
        "events",
        "artifacts",
        "approvals",
        "documents",
        "document_pages",
        "document_chunks",
        "evidence_records",
        "portfolios",
    ):
        columns = _columns(conn, table)
        if "tenant_id" not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN tenant_id TEXT")


def _migrate_runtime_local_tenant_backfill(conn: sqlite3.Connection) -> None:
    _backfill_local_tenant(conn, ("sessions", "turns", "runs", "events", "artifacts", "approvals"))


def _migrate_evidence_local_tenant_backfill(conn: sqlite3.Connection) -> None:
    _backfill_local_tenant(
        conn,
        ("documents", "document_pages", "document_chunks", "evidence_records"),
    )


def _migrate_portfolio_local_tenant_backfill(conn: sqlite3.Connection) -> None:
    _backfill_local_tenant(conn, ("portfolios",))


def _migrate_workspace_local_tenant_backfill(conn: sqlite3.Connection) -> None:
    _backfill_local_tenant(
        conn,
        (
            "workspaces",
            "projects",
            "research_cases",
            "research_case_runs",
            "workflow_templates",
            "workflow_template_runs",
            "case_assets",
            "workflow_executions",
            "case_decisions",
        ),
    )


def _backfill_local_tenant(conn: sqlite3.Connection, tables: Iterable[str]) -> None:
    for table in tables:
        if "tenant_id" in _columns(conn, table):
            conn.execute(
                f"UPDATE {table} SET tenant_id = ? WHERE tenant_id IS NULL OR tenant_id = ''",
                (LOCAL_TENANT_ID,),
            )


def _migrate_run_identity_snapshot(conn: sqlite3.Connection) -> None:
    if "identity_snapshot" not in _columns(conn, "runs"):
        conn.execute("ALTER TABLE runs ADD COLUMN identity_snapshot TEXT")


def _migrate_run_workflow_context(conn: sqlite3.Connection) -> None:
    if "workflow_context" not in _columns(conn, "runs"):
        conn.execute("ALTER TABLE runs ADD COLUMN workflow_context TEXT")


def _migrate_runtime_outbox(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_outbox (
            outbox_id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL UNIQUE,
            run_id TEXT NOT NULL,
            sequence INTEGER NOT NULL,
            payload TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            worker_id TEXT,
            leased_at TEXT,
            published_at TEXT,
            created_at TEXT NOT NULL
        )
        """
    )


def _migrate_run_queue_leases(conn: sqlite3.Connection) -> None:
    columns = _columns(conn, "run_queue")
    additions = {
        "worker_id": "TEXT",
        "leased_at": "TEXT",
        "lease_expires_at": "TEXT",
        "attempt_count": "INTEGER NOT NULL DEFAULT 0",
    }
    for column, ddl in additions.items():
        if column not in columns:
            conn.execute(f"ALTER TABLE run_queue ADD COLUMN {column} {ddl}")
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_run_queue_status_lease_queue
        ON run_queue(status, lease_expires_at, queue_id)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_run_queue_run_status
        ON run_queue(run_id, status)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_outbox_status_created
        ON runtime_outbox(status, created_at)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_outbox_run_sequence
        ON runtime_outbox(run_id, sequence)
        """
    )

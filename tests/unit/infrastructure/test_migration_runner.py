import json
import sqlite3
from pathlib import Path

from doge.infrastructure.database.agent_repositories import bootstrap_agent_schema
from doge.infrastructure.database.migration_runner import registered_migrations


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _primary_key_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    columns = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return [row[1] for row in sorted((row for row in columns if row[5]), key=lambda row: row[5])]


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone()
    return row is not None


def test_context_migration_registry_declares_context_ownership():
    migrations = registered_migrations()
    keys = {migration.key for migration in migrations}
    contexts = {migration.context for migration in migrations}
    repo_root = Path(__file__).resolve().parents[3]

    assert {
        "runtime:idempotency_key_scope",
        "evidence:documents_metadata",
        "runtime:tenant_partition_columns",
        "runtime:local_tenant_backfill",
        "evidence:local_tenant_backfill",
        "portfolio:local_tenant_backfill",
        "workspace:local_tenant_backfill",
        "runtime:run_identity_snapshot",
        "runtime:run_workflow_context",
        "runtime:runtime_outbox",
        "runtime:run_queue_leases",
        "runtime:approval_explanation_fields",
        "runtime:runtime_query_indexes",
    }.issubset(keys)
    assert {"runtime", "evidence"}.issubset(contexts)
    for context in ("runtime", "evidence", "portfolio", "governance", "workspace"):
        assert (repo_root / "migrations" / context / "README.md").exists()
        assert (
            repo_root
            / "src"
            / "doge"
            / "infrastructure"
            / "database"
            / "migrations"
            / context
            / "README.md"
        ).exists()


def test_source_local_migration_manifests_match_registry():
    migrations = registered_migrations()
    registered_by_context: dict[str, set[str]] = {}
    repo_root = Path(__file__).resolve().parents[3]
    manifest_root = repo_root / "src" / "doge" / "infrastructure" / "database" / "migrations"
    contexts = ("runtime", "evidence", "portfolio", "governance", "workspace")

    for migration in migrations:
        registered_by_context.setdefault(migration.context, set()).add(migration.name)

    for context in contexts:
        manifest_path = manifest_root / context / "manifest.json"
        assert manifest_path.exists(), f"missing migration manifest for {context}"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        assert manifest["context"] == context
        assert set(manifest["migrations"]) == registered_by_context.get(context, set())


def test_bootstrap_upgrades_legacy_agent_database_with_context_migrations(tmp_path):
    db = tmp_path / "legacy_agent_state.db"
    with sqlite3.connect(db) as conn:
        conn.executescript(
            """
            CREATE TABLE idempotency_keys (
                key TEXT PRIMARY KEY,
                scope TEXT NOT NULL,
                run_id TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE documents (
                document_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                content TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE runs (
                run_id TEXT PRIMARY KEY,
                session_id TEXT,
                workflow TEXT NOT NULL,
                question TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE run_queue (
                queue_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO idempotency_keys(key, scope, run_id, created_at)
            VALUES ('idem-1', 'scope-a', 'run-1', '2026-01-01T00:00:00Z');
            INSERT INTO documents(document_id, filename, content, status, created_at)
            VALUES ('doc-1', 'legacy.pdf', 'content', 'ready', '2026-01-01T00:00:00Z');
            INSERT INTO runs(run_id, workflow, question, status, created_at, updated_at)
            VALUES ('run-1', 'investment_research', 'q', 'pending', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z');
            INSERT INTO run_queue(run_id, status) VALUES ('run-1', 'pending');
            """
        )

    bootstrap_agent_schema(db)
    bootstrap_agent_schema(db)

    with sqlite3.connect(db) as conn:
        assert _primary_key_columns(conn, "idempotency_keys") == ["key", "scope"]
        assert conn.execute(
            "SELECT run_id FROM idempotency_keys WHERE key = ? AND scope = ?",
            ("idem-1", "scope-a"),
        ).fetchone()[0] == "run-1"

        assert {"tenant_id", "identity_snapshot"}.issubset(_columns(conn, "runs"))
        assert {
            "tenant_id",
            "original_filename",
            "file_hash",
            "parsing_status",
            "updated_at",
        }.issubset(_columns(conn, "documents"))
        assert {
            "worker_id",
            "leased_at",
            "lease_expires_at",
            "attempt_count",
        }.issubset(_columns(conn, "run_queue"))
        assert _table_exists(conn, "runtime_outbox")

        document = conn.execute(
            """
            SELECT original_filename, parsing_status, status
            FROM documents
            WHERE document_id = ?
            """,
            ("doc-1",),
        ).fetchone()
        assert document == ("legacy.pdf", "parsed", "parsed")

        applied = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM schema_migrations ORDER BY name"
            ).fetchall()
        }
        expected_applied = {
            "agent_schema_v1",
            *(migration.key for migration in registered_migrations()),
        }
        assert expected_applied.issubset(applied)
        assert len(applied) == len(expected_applied)


def test_runtime_context_migration_adds_query_indexes(tmp_path):
    db = tmp_path / "runtime_indexes.db"
    bootstrap_agent_schema(db)

    with sqlite3.connect(db) as conn:
        indexes = {
            row[1]
            for table in ("runs", "turns", "approvals", "artifacts", "run_queue")
            for row in conn.execute(f"PRAGMA index_list({table})").fetchall()
        }

    assert {
        "idx_runs_session_created",
        "idx_turns_session_created",
        "idx_approvals_run_status",
        "idx_artifacts_run_created",
        "idx_run_queue_status_worker_lease",
    }.issubset(indexes)


def test_bootstrap_adds_approval_explanation_fields_to_legacy_approvals(tmp_path):
    db = tmp_path / "legacy_approvals.db"
    with sqlite3.connect(db) as conn:
        conn.executescript(
            """
            CREATE TABLE runs (
                run_id TEXT PRIMARY KEY,
                session_id TEXT,
                workflow TEXT NOT NULL,
                question TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE approvals (
                approval_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                action TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                resolved_at TEXT
            );
            INSERT INTO runs(run_id, workflow, question, status, created_at, updated_at)
            VALUES ('run-1', 'investment_research', 'q', 'awaiting_approval', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z');
            INSERT INTO approvals(approval_id, run_id, action, risk_level, status, created_at, resolved_at)
            VALUES ('appr-1', 'run-1', 'publish memo', 'high', 'pending', '2026-01-01T00:00:00Z', NULL);
            """
        )

    bootstrap_agent_schema(db)
    bootstrap_agent_schema(db)

    with sqlite3.connect(db) as conn:
        assert {
            "why_needed",
            "impact",
            "deny_consequence",
            "publish_target",
        }.issubset(_columns(conn, "approvals"))
        row = conn.execute(
            """
            SELECT why_needed, impact, deny_consequence, publish_target
            FROM approvals
            WHERE approval_id = 'appr-1'
            """
        ).fetchone()
        assert row == ("", "", "", "")


def test_runtime_context_schema_declares_child_foreign_keys(tmp_path):
    db = tmp_path / "runtime_foreign_keys.db"
    bootstrap_agent_schema(db)

    with sqlite3.connect(db) as conn:
        foreign_keys = {
            table: {
                (row[3], row[2], row[4])
                for row in conn.execute(f"PRAGMA foreign_key_list({table})").fetchall()
            }
            for table in ("turns", "events", "artifacts", "approvals")
        }

    assert ("session_id", "sessions", "session_id") in foreign_keys["turns"]
    for table in ("events", "artifacts", "approvals"):
        assert ("run_id", "runs", "run_id") in foreign_keys[table]


def test_bootstrap_backfills_legacy_null_tenants_to_local(tmp_path):
    db = tmp_path / "legacy_local_tenant.db"
    with sqlite3.connect(db) as conn:
        conn.executescript(
            """
            CREATE TABLE sessions (
                session_id TEXT PRIMARY KEY,
                tenant_id TEXT,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE documents (
                document_id TEXT PRIMARY KEY,
                tenant_id TEXT,
                filename TEXT NOT NULL,
                content TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE portfolios (
                portfolio_id TEXT PRIMARY KEY,
                tenant_id TEXT,
                name TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE workspaces (
                workspace_id TEXT PRIMARY KEY,
                tenant_id TEXT,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                deleted_at TEXT
            );
            INSERT INTO sessions(session_id, tenant_id, title, created_at, updated_at)
            VALUES ('ses-1', NULL, 'Legacy', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z');
            INSERT INTO documents(document_id, tenant_id, filename, content, status, created_at)
            VALUES ('doc-1', '', 'legacy.pdf', 'content', 'ready', '2026-01-01T00:00:00Z');
            INSERT INTO portfolios(portfolio_id, tenant_id, name)
            VALUES ('portfolio-1', NULL, 'Legacy book');
            INSERT INTO workspaces(workspace_id, tenant_id, name, status, metadata, created_at, updated_at)
            VALUES ('wsp-1', NULL, 'Legacy workspace', 'active', '{}', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z');
            """
        )

    bootstrap_agent_schema(db)

    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT tenant_id FROM sessions WHERE session_id = 'ses-1'").fetchone()[0] == "local"
        assert conn.execute("SELECT tenant_id FROM documents WHERE document_id = 'doc-1'").fetchone()[0] == "local"
        assert conn.execute(
            "SELECT tenant_id FROM portfolios WHERE portfolio_id = 'portfolio-1'"
        ).fetchone()[0] == "local"
        assert conn.execute("SELECT tenant_id FROM workspaces WHERE workspace_id = 'wsp-1'").fetchone()[0] == "local"

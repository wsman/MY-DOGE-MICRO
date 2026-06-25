import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from doge.core.domain.agent_models import AgentEvent, AgentRun, AgentSession, EventType
from doge.core.domain.enterprise_context import IdentitySnapshot
from doge.infrastructure.database.agent_repositories import (
    SQLiteApprovalRepository,
    SQLiteArtifactRepository,
    SQLiteDocumentRepository,
    SQLiteEventRepository,
    SQLiteRunRepository,
    SQLiteSessionRepository,
    bootstrap_agent_schema,
)
from doge.shared.scope import TenantScope


def test_sqlite_run_repository_save_and_get(tmp_path):
    db = tmp_path / "agent_state.db"
    repo = SQLiteRunRepository(db)
    run = AgentRun.create(workflow="investment_research", question="q", session_id="ses-1")
    repo.save(run)

    loaded = repo.get(run.run_id)

    assert loaded is not None
    assert loaded.question == "q"
    assert loaded.session_id == "ses-1"


def test_sqlite_run_repository_local_filter_reads_legacy_null_tenant(tmp_path):
    db = tmp_path / "agent_state.db"
    repo = SQLiteRunRepository(db)
    run = AgentRun.create(workflow="investment_research", question="q", session_id="ses-1")
    repo.save(run)
    with sqlite3.connect(str(db)) as conn:
        conn.execute("UPDATE runs SET tenant_id = NULL WHERE run_id = ?", (run.run_id,))
        conn.commit()

    assert repo.get(run.run_id, tenant_id="local") is not None
    assert [item.run_id for item in repo.list_recent(tenant_id="local")] == [run.run_id]
    assert repo.get(run.run_id, tenant_id="tenant-a") is None


def test_sqlite_event_repository_sequence_order(tmp_path):
    db = tmp_path / "agent_state.db"
    run = AgentRun.create(workflow="investment_research", question="q")
    SQLiteRunRepository(db).save(run)
    events = SQLiteEventRepository(db)
    second = run.add_event(EventType.TOOL_RESULT, {"n": 2})
    first = run.add_event(EventType.RUN_CREATED, {"n": 1})
    first.sequence = 1
    second.sequence = 2
    events.append(second)
    events.append(first)

    loaded = events.list_for_run(run.run_id)

    assert [event.payload["n"] for event in loaded] == [1, 2]


def test_sqlite_event_repository_allocates_sequence_atomically(tmp_path):
    db = tmp_path / "agent_state.db"
    run = AgentRun.create(workflow="investment_research", question="q")
    SQLiteRunRepository(db).save(run)

    def append_once(index):
        event = AgentEvent(
            event_id=f"evt-{index}",
            run_id=run.run_id,
            event_type=EventType.TOOL_RESULT,
            payload={"n": index},
        )
        return SQLiteEventRepository(db).append(event).sequence

    with ThreadPoolExecutor(max_workers=8) as executor:
        sequences = list(executor.map(append_once, range(8)))

    loaded = SQLiteEventRepository(db).list_for_run(run.run_id)

    assert sorted(sequences) == list(range(1, 9))
    assert [event.sequence for event in loaded] == list(range(1, 9))


def test_sqlite_event_repository_rejects_duplicate_sequence_without_replace(tmp_path):
    db = tmp_path / "agent_state.db"
    run = AgentRun.create(workflow="investment_research", question="q")
    SQLiteRunRepository(db).save(run)
    events = SQLiteEventRepository(db)
    original = run.add_event(EventType.RUN_CREATED, {"n": 1})
    duplicate = AgentEvent(
        event_id="evt-duplicate",
        run_id=run.run_id,
        event_type=EventType.ERROR,
        payload={"n": 99},
        sequence=1,
    )
    events.append(original)

    with pytest.raises(sqlite3.IntegrityError):
        events.append(duplicate)

    loaded = events.list_for_run(run.run_id)
    assert [event.payload["n"] for event in loaded] == [1]


def test_sqlite_event_repository_rejects_orphan_run_id(tmp_path):
    db = tmp_path / "agent_state.db"
    events = SQLiteEventRepository(db)
    event = AgentEvent(
        event_id="evt-orphan",
        run_id="missing-run",
        event_type=EventType.ERROR,
        payload={"n": 1},
    )

    with pytest.raises(sqlite3.IntegrityError):
        events.append(event)


def test_sqlite_artifact_repository_roundtrip(tmp_path):
    db = tmp_path / "agent_state.db"
    run = AgentRun.create(workflow="investment_research", question="q")
    SQLiteRunRepository(db).save(run)
    artifact = run.add_artifact("memo", "Memo", "content", {"x": 1})
    SQLiteArtifactRepository(db).save(artifact)

    loaded = SQLiteArtifactRepository(db).list_for_run(run.run_id)

    assert loaded[0].content == "content"
    assert loaded[0].data == {"x": 1}


def test_sqlite_session_repository_roundtrip(tmp_path):
    db = tmp_path / "agent_state.db"
    session = AgentSession.create("Demo")
    repo = SQLiteSessionRepository(db)
    repo.save(session)

    loaded = repo.get(session.session_id)

    assert loaded is not None
    assert loaded.title == "Demo"


def test_sqlite_session_repository_accepts_tenant_scope(tmp_path):
    db = tmp_path / "agent_state.db"
    repo = SQLiteSessionRepository(db)
    scope = TenantScope.enterprise("tenant-a", "user-a")
    session = AgentSession.create("Scoped", tenant_id="tenant-a")

    repo.save(session, scope)

    assert repo.get(session.session_id, scope) is not None
    assert repo.get(session.session_id, TenantScope.enterprise("tenant-b", "user-b")) is None
    assert [item.session_id for item in repo.list_recent(scope)] == [session.session_id]


def test_sqlite_run_repository_accepts_tenant_scope(tmp_path):
    db = tmp_path / "agent_state.db"
    repo = SQLiteRunRepository(db)
    scope = TenantScope.enterprise("tenant-a", "user-a")
    run = AgentRun.create(
        workflow="investment_research",
        question="q",
        session_id="ses-a",
        identity_snapshot=IdentitySnapshot(tenant_id="tenant-a", user_hash="user-a"),
    )

    repo.save(run, scope)

    assert repo.get(run.run_id, scope) is not None
    assert repo.get_run_header(run.run_id, scope) is not None
    assert [item.run_id for item in repo.list_by_session("ses-a", scope)] == [run.run_id]
    assert [item.run_id for item in repo.list_recent(scope)] == [run.run_id]
    assert repo.get(run.run_id, TenantScope.enterprise("tenant-b", "user-b")) is None


def test_sqlite_runtime_repositories_filter_by_tenant(tmp_path):
    db = tmp_path / "agent_state.db"
    sessions = SQLiteSessionRepository(db)
    runs = SQLiteRunRepository(db)
    events = SQLiteEventRepository(db)
    artifacts = SQLiteArtifactRepository(db)
    approvals = SQLiteApprovalRepository(db)

    session_a = AgentSession.create("Tenant A", tenant_id="tenant-a")
    session_b = AgentSession.create("Tenant B", tenant_id="tenant-b")
    sessions.save(session_a)
    sessions.save(session_b)
    run_a = AgentRun.create(
        workflow="investment_research",
        question="a",
        session_id=session_a.session_id,
        identity_snapshot=IdentitySnapshot(tenant_id="tenant-a", user_hash="user-a"),
    )
    run_b = AgentRun.create(
        workflow="investment_research",
        question="b",
        session_id=session_b.session_id,
        identity_snapshot=IdentitySnapshot(tenant_id="tenant-b", user_hash="user-b"),
    )
    runs.save(run_a)
    runs.save(run_b)
    event_a = run_a.add_event(EventType.RUN_CREATED, {"tenant": "a"})
    event_b = run_b.add_event(EventType.RUN_CREATED, {"tenant": "b"})
    events.append(event_a)
    events.append(event_b)
    artifact_a = run_a.add_artifact("memo", "A", "tenant a")
    artifact_b = run_b.add_artifact("memo", "B", "tenant b")
    artifacts.save(artifact_a)
    artifacts.save(artifact_b)
    approval_a = run_a.add_approval("publish", "high")
    approval_b = run_b.add_approval("publish", "high")
    approvals.save(approval_a)
    approvals.save(approval_b)

    assert sessions.get(session_a.session_id, tenant_id="tenant-a") is not None
    assert sessions.get(session_b.session_id, tenant_id="tenant-a") is None
    assert [item.session_id for item in sessions.list_recent(tenant_id="tenant-a")] == [session_a.session_id]
    assert runs.get(run_a.run_id, tenant_id="tenant-a") is not None
    assert runs.get(run_b.run_id, tenant_id="tenant-a") is None
    assert [item.run_id for item in runs.list_by_session(session_a.session_id, tenant_id="tenant-a")] == [run_a.run_id]
    assert runs.list_by_session(session_b.session_id, tenant_id="tenant-a") == []
    assert [item.payload["tenant"] for item in events.list_for_run(run_a.run_id, tenant_id="tenant-a")] == ["a"]
    assert events.list_for_run(run_b.run_id, tenant_id="tenant-a") == []
    assert [item.artifact_id for item in artifacts.list_for_run(run_a.run_id, tenant_id="tenant-a")] == [
        artifact_a.artifact_id
    ]
    assert artifacts.list_for_run(run_b.run_id, tenant_id="tenant-a") == []
    assert approvals.get(approval_a.approval_id, tenant_id="tenant-a") is not None
    assert approvals.get(approval_b.approval_id, tenant_id="tenant-a") is None
    assert [item.approval_id for item in approvals.list_for_run(run_a.run_id, tenant_id="tenant-a")] == [
        approval_a.approval_id
    ]


def test_sqlite_runtime_repositories_reject_cross_tenant_writes(tmp_path):
    db = tmp_path / "agent_state.db"
    sessions = SQLiteSessionRepository(db)
    runs = SQLiteRunRepository(db)
    events = SQLiteEventRepository(db)
    artifacts = SQLiteArtifactRepository(db)
    approvals = SQLiteApprovalRepository(db)

    session = AgentSession.create("Tenant A", tenant_id="tenant-a")
    sessions.save(session)
    run = AgentRun.create(
        workflow="investment_research",
        question="q",
        session_id=session.session_id,
        identity_snapshot=IdentitySnapshot(tenant_id="tenant-a", user_hash="user-a"),
    )
    runs.save(run)

    with pytest.raises(ValueError, match="tenant mismatch"):
        sessions.save(session, tenant_id="tenant-b")
    with pytest.raises(ValueError, match="tenant mismatch"):
        runs.save(run, tenant_id="tenant-b")
    with pytest.raises(ValueError, match="tenant mismatch"):
        events.append(run.add_event(EventType.RUN_CREATED, {}), tenant_id="tenant-b")
    with pytest.raises(ValueError, match="tenant mismatch"):
        artifacts.save(run.add_artifact("memo", "Memo", "content"), tenant_id="tenant-b")
    with pytest.raises(ValueError, match="tenant mismatch"):
        approvals.save(run.add_approval("publish", "high"), tenant_id="tenant-b")


def test_sqlite_document_repository_rejects_cross_tenant_overwrite(tmp_path):
    db = tmp_path / "agent_state.db"
    repo = SQLiteDocumentRepository(db)
    repo.save({"document_id": "doc-a", "tenant_id": "tenant-a", "filename": "a.txt", "content": "alpha"})

    with pytest.raises(ValueError, match="tenant mismatch"):
        repo.save({"document_id": "doc-a", "tenant_id": "tenant-b", "filename": "b.txt", "content": "beta"})


def test_bootstrap_adds_tenant_columns_to_legacy_agent_tables(tmp_path):
    db = tmp_path / "legacy_agent_state.db"
    with sqlite3.connect(db) as conn:
        conn.executescript(
            """
            CREATE TABLE sessions (
                session_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE turns (
                turn_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                user_message TEXT NOT NULL,
                run_id TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE runs (
                run_id TEXT PRIMARY KEY,
                session_id TEXT,
                workflow TEXT NOT NULL,
                question TEXT NOT NULL,
                market TEXT DEFAULT 'us',
                language TEXT DEFAULT 'en',
                document_ids TEXT,
                portfolio_id TEXT,
                model_policy TEXT,
                status TEXT NOT NULL,
                cancel_requested_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                schema_version TEXT DEFAULT '1.0'
            );
            CREATE TABLE events (
                event_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                schema_version TEXT DEFAULT '1.0',
                created_at TEXT NOT NULL,
                UNIQUE(run_id, sequence)
            );
            CREATE TABLE artifacts (
                artifact_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                data TEXT,
                created_at TEXT NOT NULL
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
            CREATE TABLE document_pages (
                page_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                page_number INTEGER NOT NULL,
                text TEXT NOT NULL DEFAULT '',
                image_metadata TEXT,
                source_hash TEXT,
                parser_error TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(document_id, page_number)
            );
            CREATE TABLE document_chunks (
                chunk_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                page_id TEXT NOT NULL,
                page_number INTEGER NOT NULL,
                text TEXT NOT NULL,
                start_char INTEGER NOT NULL,
                end_char INTEGER NOT NULL,
                source_hash TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE evidence_records (
                evidence_id TEXT PRIMARY KEY,
                run_id TEXT,
                document_id TEXT NOT NULL,
                page_id TEXT NOT NULL,
                chunk_id TEXT NOT NULL,
                page_number INTEGER NOT NULL,
                claim TEXT NOT NULL DEFAULT '',
                support_snippet TEXT NOT NULL,
                relevance_score REAL,
                metadata TEXT,
                created_at TEXT NOT NULL
            );
            """
        )

    bootstrap_agent_schema(db)

    with sqlite3.connect(db) as conn:
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
            columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
            assert "tenant_id" in columns


def test_sqlite_document_repository_filters_by_tenant(tmp_path):
    db = tmp_path / "agent_state.db"
    repo = SQLiteDocumentRepository(db)
    repo.save({"document_id": "doc-a", "tenant_id": "tenant-a", "filename": "a.txt", "content": "alpha"})
    repo.save({"document_id": "doc-b", "tenant_id": "tenant-b", "filename": "b.txt", "content": "beta"})

    assert repo.get("doc-a", tenant_id="tenant-a") is not None
    assert repo.get("doc-b", tenant_id="tenant-a") is None
    assert [row["document_id"] for row in repo.list_recent(tenant_id="tenant-a")] == ["doc-a"]

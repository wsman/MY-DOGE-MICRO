from doge.core.domain.agent_models import AgentRun, AgentSession, EventType
from doge.infrastructure.database.agent_repositories import (
    SQLiteArtifactRepository,
    SQLiteEventRepository,
    SQLiteRunRepository,
    SQLiteSessionRepository,
)


def test_sqlite_run_repository_save_and_get(tmp_path):
    db = tmp_path / "agent_state.db"
    repo = SQLiteRunRepository(db)
    run = AgentRun.create(workflow="investment_research", question="q", session_id="ses-1")
    repo.save(run)

    loaded = repo.get(run.run_id)

    assert loaded is not None
    assert loaded.question == "q"
    assert loaded.session_id == "ses-1"


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

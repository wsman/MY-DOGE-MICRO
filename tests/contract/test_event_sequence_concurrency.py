from concurrent.futures import ThreadPoolExecutor

from doge.core.domain.agent_models import AgentEvent, AgentRun, EventType
from doge.infrastructure.database import agent_repositories
from doge.infrastructure.database.agent_repositories import SQLiteEventRepository, SQLiteRunRepository


def test_concurrent_event_appends_allocate_gap_free_sequences(tmp_path):
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
        sequences = list(executor.map(append_once, range(16)))

    loaded = SQLiteEventRepository(db).list_for_run(run.run_id)

    assert sorted(sequences) == list(range(1, 17))
    assert [event.sequence for event in loaded] == list(range(1, 17))
    assert sorted(event.payload["n"] for event in loaded) == list(range(16))


def test_event_repository_source_rejects_replace_semantics():
    source = agent_repositories.__file__
    assert source is not None
    with open(source, encoding="utf-8") as handle:
        content = handle.read()

    assert "INSERT OR REPLACE INTO events" not in content

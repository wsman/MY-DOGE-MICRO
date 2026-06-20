from doge.core.domain.agent_models import AgentRun, AgentSession
from doge.infrastructure.database.agent_repositories import (
    SQLiteRunRepository,
    SQLiteSessionRepository,
    bootstrap_agent_schema,
)


def test_agent_schema_bootstrap_is_idempotent(tmp_path):
    db = tmp_path / "agent_state.db"

    bootstrap_agent_schema(db)
    bootstrap_agent_schema(db)

    session = AgentSession.create("Idempotent")
    SQLiteSessionRepository(db).save(session)
    run = AgentRun.create(workflow="investment_research", question="q", session_id=session.session_id)
    SQLiteRunRepository(db).save(run)

    assert SQLiteRunRepository(db).get(run.run_id) is not None

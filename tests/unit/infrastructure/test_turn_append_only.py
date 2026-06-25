"""Regression coverage for append-only session turns."""

from __future__ import annotations

from pathlib import Path

from doge.core.domain.agent_models import AgentSession, AgentTurn
from doge.infrastructure.database.agent_repositories import SQLiteSessionRepository


def test_session_save_does_not_delete_existing_turns(tmp_path) -> None:
    db = tmp_path / "agent_state.db"
    repo = SQLiteSessionRepository(db)
    session = AgentSession.create("Initial")
    first_turn = AgentTurn.create(
        session_id=session.session_id,
        user_message="Analyze AAPL",
        run_id="run-1",
    )
    session.turns.append(first_turn)
    repo.save(session)

    metadata_update = AgentSession(
        session_id=session.session_id,
        tenant_id=session.tenant_id,
        title="Renamed",
        created_at=session.created_at,
        updated_at=session.updated_at,
        turns=[],
    )
    repo.save(metadata_update)

    loaded = repo.get(session.session_id)
    assert loaded is not None
    assert loaded.title == "Renamed"
    assert [turn.turn_id for turn in loaded.turns] == [first_turn.turn_id]
    assert loaded.turns[0].user_message == "Analyze AAPL"


def test_session_repository_source_has_no_turn_delete_reinsert_path() -> None:
    source = Path("src/doge/infrastructure/database/agent_repositories.py").read_text(encoding="utf-8")

    assert "DELETE FROM " + "turns" not in source

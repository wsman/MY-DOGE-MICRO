"""Use cases for local agent sessions."""

from __future__ import annotations

from doge.core.domain.agent_models import AgentSession, AgentTurn, utc_now
from doge.core.ports.agent_repository import ISessionRepository


class CreateSession:
    def __init__(self, sessions: ISessionRepository) -> None:
        self._sessions = sessions

    def execute(self, title: str = "Research session") -> AgentSession:
        session = AgentSession.create(title=title)
        self._sessions.save(session)
        return session


class ResumeSession:
    def __init__(self, sessions: ISessionRepository) -> None:
        self._sessions = sessions

    def execute(self, session_id: str) -> AgentSession | None:
        return self._sessions.get(session_id)


class ListSessions:
    def __init__(self, sessions: ISessionRepository) -> None:
        self._sessions = sessions

    def execute(self, limit: int = 20) -> list[AgentSession]:
        return self._sessions.list_recent(limit)


class AppendTurn:
    def __init__(self, sessions: ISessionRepository) -> None:
        self._sessions = sessions

    def execute(self, session_id: str, user_message: str, run_id: str | None = None) -> AgentTurn:
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(f"session not found: {session_id}")
        turn = AgentTurn.create(session_id=session_id, user_message=user_message, run_id=run_id)
        session.turns.append(turn)
        session.updated_at = utc_now()
        self._sessions.save(session)
        return turn

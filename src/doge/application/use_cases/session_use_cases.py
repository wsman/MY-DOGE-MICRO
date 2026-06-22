"""Use cases for local agent sessions."""

from __future__ import annotations

from doge.core.domain.agent_models import AgentSession, AgentTurn, utc_now
from doge.core.ports.agent_repository import ISessionRepository


class CreateSession:
    def __init__(self, sessions: ISessionRepository) -> None:
        self._sessions = sessions

    def execute(self, title: str = "Research session", *, tenant_id: str | None = None) -> AgentSession:
        session = AgentSession.create(title=title, tenant_id=tenant_id)
        self._sessions.save(session, tenant_id=tenant_id)
        return session


class ResumeSession:
    def __init__(self, sessions: ISessionRepository) -> None:
        self._sessions = sessions

    def execute(self, session_id: str, *, tenant_id: str | None = None) -> AgentSession | None:
        return self._sessions.get(session_id, tenant_id=tenant_id)


class ListSessions:
    def __init__(self, sessions: ISessionRepository) -> None:
        self._sessions = sessions

    def execute(self, limit: int = 20, *, tenant_id: str | None = None) -> list[AgentSession]:
        return self._sessions.list_recent(limit, tenant_id=tenant_id)


class AppendTurn:
    def __init__(self, sessions: ISessionRepository) -> None:
        self._sessions = sessions

    def execute(
        self,
        session_id: str,
        user_message: str,
        run_id: str | None = None,
        *,
        tenant_id: str | None = None,
    ) -> AgentTurn:
        session = self._sessions.get(session_id, tenant_id=tenant_id)
        if session is None:
            raise KeyError(f"session not found: {session_id}")
        effective_tenant_id = tenant_id if tenant_id is not None else session.tenant_id
        turn = AgentTurn.create(
            session_id=session_id,
            user_message=user_message,
            run_id=run_id,
            tenant_id=effective_tenant_id,
        )
        session.turns.append(turn)
        session.updated_at = utc_now()
        self._sessions.save(session, tenant_id=effective_tenant_id)
        return turn

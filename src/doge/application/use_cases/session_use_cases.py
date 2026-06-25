"""Use cases for local agent sessions."""

from __future__ import annotations

from doge.core.domain.agent_models import AgentSession, AgentTurn, utc_now
from doge.core.ports.agent_repository import ISessionRepository
from doge.shared.scope import TenantScope


def _scope_for_session(scope: TenantScope | None, tenant_id: str | None) -> TenantScope:
    if scope is None:
        return TenantScope.from_tenant_id(tenant_id)
    if tenant_id is not None and tenant_id != scope.tenant_id:
        raise ValueError(f"tenant mismatch for session use case: {tenant_id} != {scope.tenant_id}")
    return scope


class CreateSession:
    def __init__(self, sessions: ISessionRepository) -> None:
        self._sessions = sessions

    def execute(
        self,
        title: str = "Research session",
        *,
        scope: TenantScope | None = None,
        tenant_id: str | None = None,
    ) -> AgentSession:
        resolved_scope = _scope_for_session(scope, tenant_id)
        session = AgentSession.create(title=title, tenant_id=resolved_scope.tenant_id)
        self._sessions.save(session, resolved_scope)
        return session


class ResumeSession:
    def __init__(self, sessions: ISessionRepository) -> None:
        self._sessions = sessions

    def execute(
        self,
        session_id: str,
        *,
        scope: TenantScope | None = None,
        tenant_id: str | None = None,
    ) -> AgentSession | None:
        return self._sessions.get(session_id, _scope_for_session(scope, tenant_id))


class ListSessions:
    def __init__(self, sessions: ISessionRepository) -> None:
        self._sessions = sessions

    def execute(
        self,
        limit: int = 20,
        *,
        scope: TenantScope | None = None,
        tenant_id: str | None = None,
    ) -> list[AgentSession]:
        return self._sessions.list_recent(_scope_for_session(scope, tenant_id), limit)


class AppendTurn:
    def __init__(self, sessions: ISessionRepository) -> None:
        self._sessions = sessions

    def execute(
        self,
        session_id: str,
        user_message: str,
        run_id: str | None = None,
        *,
        scope: TenantScope | None = None,
        tenant_id: str | None = None,
    ) -> AgentTurn:
        resolved_scope = _scope_for_session(scope, tenant_id)
        session = self._sessions.get(session_id, resolved_scope)
        if session is None:
            raise KeyError(f"session not found: {session_id}")
        turn = AgentTurn.create(
            session_id=session_id,
            user_message=user_message,
            run_id=run_id,
            tenant_id=resolved_scope.tenant_id,
        )
        session.turns.append(turn)
        session.updated_at = utc_now()
        self._sessions.save(session, resolved_scope)
        return turn

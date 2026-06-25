from __future__ import annotations

import pytest

from doge.application.use_cases.session_use_cases import AppendTurn, CreateSession, ListSessions, ResumeSession
from doge.core.domain.agent_models import AgentSession
from doge.shared.scope import TenantScope


class FakeSessions:
    def __init__(self) -> None:
        self.items: dict[str, AgentSession] = {}
        self.saved_tenants: list[str | None] = []

    def save(self, session, scope=None, *, tenant_id=None):
        tenant = getattr(scope, "tenant_id", scope) if scope is not None else tenant_id
        session.tenant_id = tenant
        self.saved_tenants.append(tenant)
        self.items[session.session_id] = session

    def get(self, session_id, scope=None, *, tenant_id=None):
        tenant = getattr(scope, "tenant_id", scope) if scope is not None else tenant_id
        session = self.items.get(session_id)
        if session is None or (tenant is not None and session.tenant_id != tenant):
            return None
        return session

    def list_recent(self, scope=None, limit=20, *, tenant_id=None):
        if isinstance(scope, int):
            limit = scope
            scope = None
        tenant = getattr(scope, "tenant_id", scope) if scope is not None else tenant_id
        return [
            item for item in list(self.items.values())[:limit]
            if tenant is None or item.tenant_id == tenant
        ]


def test_session_use_cases_accept_tenant_scope() -> None:
    sessions = FakeSessions()
    scope = TenantScope.enterprise("tenant-a", subject_hash="user-a")

    created = CreateSession(sessions).execute("Scoped", scope=scope)
    resumed = ResumeSession(sessions).execute(created.session_id, scope=scope)
    listed = ListSessions(sessions).execute(scope=scope)
    turn = AppendTurn(sessions).execute(created.session_id, "Analyze AAPL", "run-1", scope=scope)

    assert created.tenant_id == "tenant-a"
    assert resumed == created
    assert listed == [created]
    assert turn.tenant_id == "tenant-a"
    assert sessions.saved_tenants == ["tenant-a", "tenant-a"]


def test_session_use_cases_reject_scope_tenant_id_mismatch() -> None:
    sessions = FakeSessions()
    scope = TenantScope.enterprise("tenant-a")

    with pytest.raises(ValueError, match="tenant mismatch"):
        CreateSession(sessions).execute("Mismatch", scope=scope, tenant_id="tenant-b")


def test_session_use_cases_default_to_local_scope() -> None:
    sessions = FakeSessions()

    created = CreateSession(sessions).execute("Local")
    listed = ListSessions(sessions).execute()

    assert created.tenant_id == "local"
    assert listed == [created]

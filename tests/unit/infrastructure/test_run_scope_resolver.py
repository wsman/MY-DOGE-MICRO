"""Tests for SQLiteRunScopeResolver."""

from __future__ import annotations

import pytest

from doge.core.domain.agent_models import AgentRun, IdentitySnapshot, RunStatus
from doge.core.domain.model_policy import ModelPolicy
from doge.core.domain.run_execution_context import WorkflowRunContext
from doge.infrastructure.database.run_scope_resolver import SQLiteRunScopeResolver
from doge.infrastructure.database.agent_repositories import SQLiteRunRepository
from doge.shared.scope import TenantScope


@pytest.fixture
def resolver(tmp_path):
    return SQLiteRunScopeResolver(tmp_path / "agent_state.db")


@pytest.fixture
def run_repository(tmp_path):
    return SQLiteRunRepository(tmp_path / "agent_state.db")


def _make_run(run_id: str, tenant_id: str | None, user_hash: str | None = None) -> AgentRun:
    snapshot = None
    if tenant_id is not None:
        snapshot = IdentitySnapshot(tenant_id=tenant_id, user_hash=user_hash)
    return AgentRun(
        run_id=run_id,
        session_id="ses-1",
        workflow="investment_research",
        question="Q",
        market="us",
        language="en",
        document_ids=[],
        portfolio_id=None,
        model_policy=ModelPolicy(),
        workflow_context=WorkflowRunContext(workflow="investment_research"),
        identity_snapshot=snapshot,
        status=RunStatus.QUEUED,
    )


def test_resolver_returns_local_for_missing_run(resolver):
    scope = resolver.resolve_scope("missing-run")
    assert scope.tenant_id == "local"


def test_resolver_returns_local_for_null_tenant_run(resolver, run_repository):
    run = _make_run("run-local", None)
    run_repository.save(run, TenantScope.local())

    scope = resolver.resolve_scope("run-local")
    assert scope.tenant_id == "local"


def test_resolver_returns_enterprise_scope_from_identity_snapshot(resolver, run_repository):
    run = _make_run("run-ent", "tenant-a", "user-hash-a")
    run_repository.save(run, TenantScope.enterprise("tenant-a", "user-hash-a"))

    scope = resolver.resolve_scope("run-ent")
    assert scope.tenant_id == "tenant-a"
    assert scope.subject_hash == "user-hash-a"


def test_resolver_returns_enterprise_scope_without_user_hash(resolver, run_repository):
    run = _make_run("run-ent-no-user", "tenant-b", None)
    run_repository.save(run, TenantScope.enterprise("tenant-b"))

    scope = resolver.resolve_scope("run-ent-no-user")
    assert scope.tenant_id == "tenant-b"
    assert scope.subject_hash is None

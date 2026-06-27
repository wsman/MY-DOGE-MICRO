"""Shared argument-resolution helpers for runtime collaborators."""

from __future__ import annotations

from typing import Any

from doge.core.domain.agent_models import AgentRun
from doge.core.domain.enterprise_context import IdentitySnapshot
from doge.core.domain.model_policy import ModelPolicy
from doge.shared.errors import SafeError
from doge.shared.scope import TenantScope


def identity_snapshot_from_request(request: dict[str, Any], model_policy_payload: Any) -> IdentitySnapshot | None:
    return (
        IdentitySnapshot.from_mapping(request.get("identity_snapshot"))
        or IdentitySnapshot.from_mapping(model_policy_payload if isinstance(model_policy_payload, dict) else None)
    )


def tenant_id_for_run(run: AgentRun) -> str | None:
    if run.identity_snapshot is None:
        return None
    return run.identity_snapshot.tenant_id


def run_args(
    scope: TenantScope | str | None,
    run_id: str | None,
    *,
    tenant_id: str | None = None,
) -> tuple[TenantScope, str]:
    if isinstance(scope, TenantScope):
        if run_id is None:
            raise TypeError("run_id is required")
        return scope, run_id
    if isinstance(scope, str) and run_id is None:
        return TenantScope.from_tenant_id(tenant_id), scope
    if scope is None and run_id is not None:
        return TenantScope.from_tenant_id(tenant_id), run_id
    raise TypeError("expected (scope, run_id) or legacy (run_id)")


def list_runs_args(
    scope: TenantScope | str | None,
    session_id: str | None,
    *,
    tenant_id: str | None = None,
) -> tuple[TenantScope, str | None]:
    if isinstance(scope, TenantScope):
        return scope, session_id
    if isinstance(scope, str):
        return TenantScope.from_tenant_id(tenant_id), scope
    return TenantScope.from_tenant_id(tenant_id), session_id


def queue_args(
    scope: TenantScope | str | None,
    run_id: str | None,
    reason: str,
    *,
    tenant_id: str | None = None,
) -> tuple[TenantScope, str, str]:
    if isinstance(scope, TenantScope):
        if run_id is None:
            raise TypeError("run_id is required")
        return scope, run_id, reason
    if isinstance(scope, str):
        if run_id is not None and reason == "queued":
            return TenantScope.from_tenant_id(tenant_id), scope, run_id
        return TenantScope.from_tenant_id(tenant_id), scope, reason
    raise TypeError("expected (scope, run_id) or legacy (run_id)")


def approval_args(
    scope: TenantScope | str | None,
    run_id: str | None,
    approval_id: str | bool | None,
    approved: bool,
    *,
    tenant_id: str | None = None,
) -> tuple[TenantScope, str, str, bool]:
    if isinstance(scope, TenantScope):
        if run_id is None or not isinstance(approval_id, str):
            raise TypeError("run_id and approval_id are required")
        return scope, run_id, approval_id, approved
    if isinstance(scope, str) and isinstance(run_id, str) and isinstance(approval_id, bool):
        return TenantScope.from_tenant_id(tenant_id), scope, run_id, approval_id
    raise TypeError("expected (scope, run_id, approval_id, approved) or legacy (run_id, approval_id, approved)")


def failure_args(
    scope: TenantScope | str | None,
    run_id: str | None,
    message: str | None,
    *,
    tenant_id: str | None = None,
) -> tuple[TenantScope, str, str]:
    if isinstance(scope, TenantScope):
        if run_id is None or message is None:
            raise TypeError("run_id and message are required")
        return scope, run_id, message
    if isinstance(scope, str) and run_id is not None and message is None:
        return TenantScope.from_tenant_id(tenant_id), scope, run_id
    raise TypeError("expected (scope, run_id, message) or legacy (run_id, message)")


def tool_safe_error_payload(result: Any) -> dict[str, str] | None:
    safe_error = getattr(result, "safe_error", None)
    if safe_error is not None:
        return dict(safe_error)
    if not getattr(result, "error", None):
        return None
    return SafeError.create("tool_execution_failed", str(result.error)).to_event_payload()

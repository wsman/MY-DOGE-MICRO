"""Shared argument-resolution helpers for runtime collaborators."""

from __future__ import annotations

from typing import Any
import warnings

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


def create_run_args(
    scope: TenantScope | dict[str, Any],
    request: dict[str, Any] | None,
    *,
    tenant_id: str | None = None,
) -> tuple[TenantScope, dict[str, Any]]:
    if isinstance(scope, TenantScope):
        if request is None:
            raise TypeError("request is required")
        ensure_tenant_match(scope, tenant_id)
        return scope, request_for_scope(scope, request)
    if isinstance(scope, dict) and request is None:
        legacy_scope = _scope_from_legacy_request(scope, tenant_id=tenant_id)
        warn_legacy_runtime_signature("create_run")
        return legacy_scope, request_for_scope(legacy_scope, scope)
    raise TypeError("expected (scope, request) or legacy (request)")


def run_execution_args(
    scope: TenantScope | str | None,
    run_id: str | None,
    *,
    tenant_id: str | None = None,
) -> tuple[TenantScope, str]:
    resolved_scope, resolved_run_id = run_args(scope, run_id, tenant_id=tenant_id)
    return resolved_scope, resolved_run_id


def run_args(
    scope: TenantScope | str | None,
    run_id: str | None,
    *,
    tenant_id: str | None = None,
) -> tuple[TenantScope, str]:
    if isinstance(scope, TenantScope):
        if run_id is None:
            raise TypeError("run_id is required")
        ensure_tenant_match(scope, tenant_id)
        return scope, run_id
    if isinstance(scope, str) and run_id is None:
        warn_legacy_runtime_signature("run")
        return TenantScope.from_tenant_id(tenant_id), scope
    if scope is None and run_id is not None:
        warn_legacy_runtime_signature("run")
        return TenantScope.from_tenant_id(tenant_id), run_id
    raise TypeError("expected (scope, run_id) or legacy (run_id)")


def list_runs_args(
    scope: TenantScope | str | None,
    session_id: str | None,
    *,
    tenant_id: str | None = None,
) -> tuple[TenantScope, str | None]:
    if isinstance(scope, TenantScope):
        ensure_tenant_match(scope, tenant_id)
        return scope, session_id
    if isinstance(scope, str):
        warn_legacy_runtime_signature("list_runs")
        return TenantScope.from_tenant_id(tenant_id), scope
    if tenant_id is not None:
        warn_legacy_runtime_signature("list_runs")
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
        ensure_tenant_match(scope, tenant_id)
        return scope, run_id, reason
    if isinstance(scope, str):
        warn_legacy_runtime_signature("queue_run")
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
        ensure_tenant_match(scope, tenant_id)
        return scope, run_id, approval_id, approved
    if isinstance(scope, str) and isinstance(run_id, str) and isinstance(approval_id, bool):
        warn_legacy_runtime_signature("resolve_approval")
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
        ensure_tenant_match(scope, tenant_id)
        return scope, run_id, message
    if isinstance(scope, str) and run_id is not None and message is None:
        warn_legacy_runtime_signature("record_failure")
        return TenantScope.from_tenant_id(tenant_id), scope, run_id
    raise TypeError("expected (scope, run_id, message) or legacy (run_id, message)")


def tool_safe_error_payload(result: Any) -> dict[str, str] | None:
    safe_error = getattr(result, "safe_error", None)
    if safe_error is not None:
        return dict(safe_error)
    if not getattr(result, "error", None):
        return None
    return SafeError.create("tool_execution_failed", str(result.error)).to_event_payload()


def request_for_scope(scope: TenantScope, request: dict[str, Any]) -> dict[str, Any]:
    scoped_request = dict(request)
    raw_snapshot = request.get("identity_snapshot")
    snapshot = IdentitySnapshot.from_mapping(raw_snapshot)
    if snapshot is not None and snapshot.tenant_id != scope.tenant_id:
        raise ValueError(f"tenant mismatch for run request: {snapshot.tenant_id} != {scope.tenant_id}")
    if scope.subject_hash is not None and _raw_user_hash(raw_snapshot) not in (None, scope.subject_hash):
        raise ValueError("subject mismatch for run request")
    snapshot_payload = snapshot.to_dict() if snapshot is not None else {}
    snapshot_payload["tenant_id"] = scope.tenant_id
    if scope.subject_hash is not None:
        snapshot_payload["user_hash"] = scope.subject_hash
    scoped_request["identity_snapshot"] = snapshot_payload
    return scoped_request


def ensure_tenant_match(scope: TenantScope, tenant_id: str | None) -> None:
    if tenant_id is not None and tenant_id != scope.tenant_id:
        raise ValueError(f"tenant mismatch for scope: {tenant_id} != {scope.tenant_id}")


def warn_legacy_runtime_signature(operation: str) -> None:
    warnings.warn(
        f"legacy raw tenant runtime signature used for {operation}; pass TenantScope explicitly",
        DeprecationWarning,
        stacklevel=3,
    )


def _raw_user_hash(raw_snapshot: Any) -> str | None:
    if isinstance(raw_snapshot, IdentitySnapshot):
        return raw_snapshot.user_hash
    if isinstance(raw_snapshot, dict) and "user_hash" in raw_snapshot:
        value = raw_snapshot.get("user_hash")
        return str(value) if value is not None else None
    return None


def _scope_from_legacy_request(
    request: dict[str, Any],
    *,
    tenant_id: str | None = None,
) -> TenantScope:
    snapshot = IdentitySnapshot.from_mapping(request.get("identity_snapshot"))
    if snapshot is None:
        return TenantScope.from_tenant_id(tenant_id)
    if tenant_id is not None and tenant_id != snapshot.tenant_id:
        raise ValueError(f"tenant mismatch for run request: {snapshot.tenant_id} != {tenant_id}")
    return TenantScope.enterprise(snapshot.tenant_id, snapshot.user_hash)

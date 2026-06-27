"""Persisted research-agent runtime adapter."""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator

from doge.application.agent.runtime_kernel import RuntimeKernel
from doge.core.domain.agent_models import AgentArtifact, AgentEvent, AgentRun
from doge.core.domain.enterprise_context import IdentitySnapshot
from doge.core.ports.agent_runtime import IResearchAgentRuntime
from doge.shared.scope import TenantScope


class PersistedResearchAgentRuntime(IResearchAgentRuntime):
    """Research runtime backed by repositories and the common runtime kernel."""

    def __init__(self, kernel: RuntimeKernel) -> None:
        self._kernel = kernel

    async def create_run(
        self,
        scope: TenantScope | dict[str, Any],
        request: dict[str, Any] | None = None,
        *,
        tenant_id: str | None = None,
    ) -> AgentRun:
        resolved_request, resolved_tenant_id = _create_run_args(scope, request, tenant_id=tenant_id)
        return await self._kernel.create_run(resolved_request, tenant_id=resolved_tenant_id)

    async def run_to_pause_or_completion(
        self,
        scope: TenantScope | str | None,
        run_id: str | None = None,
        *,
        tenant_id: str | None = None,
    ) -> AgentRun:
        resolved_run_id, resolved_tenant_id = _run_execution_args(scope, run_id, tenant_id=tenant_id)
        return await self._kernel.run_to_pause_or_completion(resolved_run_id, tenant_id=resolved_tenant_id)

    async def queue_run(
        self,
        scope: TenantScope | str | None,
        run_id: str | None = None,
        reason: str = "queued",
        *,
        tenant_id: str | None = None,
    ) -> AgentRun:
        resolved_scope, resolved_run_id, resolved_reason = _queue_args(scope, run_id, reason, tenant_id=tenant_id)
        return await self._kernel.queue_run(resolved_scope, resolved_run_id, resolved_reason)

    def get_run(
        self,
        scope: TenantScope | str | None,
        run_id: str | None = None,
        *,
        tenant_id: str | None = None,
    ) -> AgentRun | None:
        resolved_scope, resolved_run_id = _run_args(scope, run_id, tenant_id=tenant_id)
        return self._kernel.get_run(resolved_scope, resolved_run_id)

    def list_runs(
        self,
        scope: TenantScope | str | None = None,
        session_id: str | None = None,
        limit: int = 20,
        *,
        tenant_id: str | None = None,
    ) -> list[AgentRun]:
        resolved_scope, resolved_session_id = _list_runs_args(scope, session_id, tenant_id=tenant_id)
        return self._kernel.list_runs(resolved_scope, resolved_session_id, limit)

    def list_events(
        self,
        scope: TenantScope | str | None,
        run_id: str | None = None,
        *,
        tenant_id: str | None = None,
    ) -> list[AgentEvent]:
        resolved_scope, resolved_run_id = _run_args(scope, run_id, tenant_id=tenant_id)
        return self._kernel.list_events(resolved_scope, resolved_run_id)

    def list_artifacts(
        self,
        scope: TenantScope | str | None,
        run_id: str | None = None,
        *,
        tenant_id: str | None = None,
    ) -> list[AgentArtifact]:
        resolved_scope, resolved_run_id = _run_args(scope, run_id, tenant_id=tenant_id)
        return self._kernel.list_artifacts(resolved_scope, resolved_run_id)

    async def stream_events(
        self,
        scope: TenantScope | str | None,
        run_id: str | None = None,
        *,
        tenant_id: str | None = None,
    ) -> AsyncIterator[AgentEvent]:
        """Replay-only iterator over events already persisted for the run.

        This method yields the same events returned by ``list_events``
        asynchronously. It does **not** subscribe to new events generated after
        the call begins. Live streaming is provided by ``RunStreamHandler``
        in conjunction with ``IEventSubscriber.subscribe``.
        """
        resolved_scope, resolved_run_id = _run_args(scope, run_id, tenant_id=tenant_id)
        for event in self.list_events(resolved_scope, resolved_run_id):
            yield event
            await asyncio.sleep(0)

    async def resolve_approval(
        self,
        scope: TenantScope | str | None,
        run_id: str | None = None,
        approval_id: str | bool | None = None,
        approved: bool = True,
        *,
        tenant_id: str | None = None,
    ) -> AgentRun:
        resolved_scope, resolved_run_id, resolved_approval_id, resolved_approved = _approval_args(
            scope,
            run_id,
            approval_id,
            approved,
            tenant_id=tenant_id,
        )
        return await self._kernel.resolve_approval(
            resolved_scope,
            resolved_run_id,
            resolved_approval_id,
            resolved_approved,
        )

    async def cancel_run(
        self,
        scope: TenantScope | str | None,
        run_id: str | None = None,
        *,
        tenant_id: str | None = None,
    ) -> AgentRun:
        resolved_scope, resolved_run_id = _run_args(scope, run_id, tenant_id=tenant_id)
        return await self._kernel.cancel_run(resolved_scope, resolved_run_id)

    async def finalize_cancelled(
        self,
        scope: TenantScope | str | None,
        run_id: str | None = None,
        *,
        tenant_id: str | None = None,
    ) -> AgentRun:
        resolved_scope, resolved_run_id = _run_args(scope, run_id, tenant_id=tenant_id)
        return await self._kernel.finalize_cancelled(resolved_scope, resolved_run_id)

    async def record_failure(
        self,
        scope: TenantScope | str | None,
        run_id: str | None = None,
        message: str | None = None,
        *,
        tenant_id: str | None = None,
    ) -> AgentRun:
        resolved_scope, resolved_run_id, resolved_message = _failure_args(scope, run_id, message, tenant_id=tenant_id)
        return await self._kernel.record_failure(resolved_scope, resolved_run_id, resolved_message)


def _create_run_args(
    scope: TenantScope | dict[str, Any],
    request: dict[str, Any] | None,
    *,
    tenant_id: str | None = None,
) -> tuple[dict[str, Any], str | None]:
    if isinstance(scope, TenantScope):
        if request is None:
            raise TypeError("request is required")
        _ensure_tenant_match(scope, tenant_id)
        return _request_for_scope(scope, request), scope.tenant_id
    if isinstance(scope, dict) and request is None:
        return scope, tenant_id
    raise TypeError("expected (scope, request) or legacy (request)")


def _run_execution_args(
    scope: TenantScope | str | None,
    run_id: str | None,
    *,
    tenant_id: str | None = None,
) -> tuple[str, str | None]:
    if isinstance(scope, TenantScope):
        if run_id is None:
            raise TypeError("run_id is required")
        _ensure_tenant_match(scope, tenant_id)
        return run_id, scope.tenant_id
    if isinstance(scope, str) and run_id is None:
        return scope, tenant_id
    if scope is None and run_id is not None:
        return run_id, tenant_id
    raise TypeError("expected (scope, run_id) or legacy (run_id)")


def _run_args(
    scope: TenantScope | str | None,
    run_id: str | None,
    *,
    tenant_id: str | None = None,
) -> tuple[TenantScope, str]:
    if isinstance(scope, TenantScope):
        if run_id is None:
            raise TypeError("run_id is required")
        _ensure_tenant_match(scope, tenant_id)
        return scope, run_id
    if isinstance(scope, str) and run_id is None:
        return TenantScope.from_tenant_id(tenant_id), scope
    if scope is None and run_id is not None:
        return TenantScope.from_tenant_id(tenant_id), run_id
    raise TypeError("expected (scope, run_id) or legacy (run_id)")


def _list_runs_args(
    scope: TenantScope | str | None,
    session_id: str | None,
    *,
    tenant_id: str | None = None,
) -> tuple[TenantScope, str | None]:
    if isinstance(scope, TenantScope):
        _ensure_tenant_match(scope, tenant_id)
        return scope, session_id
    if isinstance(scope, str):
        return TenantScope.from_tenant_id(tenant_id), scope
    return TenantScope.from_tenant_id(tenant_id), session_id


def _queue_args(
    scope: TenantScope | str | None,
    run_id: str | None,
    reason: str,
    *,
    tenant_id: str | None = None,
) -> tuple[TenantScope, str, str]:
    if isinstance(scope, TenantScope):
        if run_id is None:
            raise TypeError("run_id is required")
        _ensure_tenant_match(scope, tenant_id)
        return scope, run_id, reason
    if isinstance(scope, str):
        if run_id is not None and reason == "queued":
            return TenantScope.from_tenant_id(tenant_id), scope, run_id
        return TenantScope.from_tenant_id(tenant_id), scope, reason
    raise TypeError("expected (scope, run_id) or legacy (run_id)")


def _approval_args(
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
        _ensure_tenant_match(scope, tenant_id)
        return scope, run_id, approval_id, approved
    if isinstance(scope, str) and isinstance(run_id, str) and isinstance(approval_id, bool):
        return TenantScope.from_tenant_id(tenant_id), scope, run_id, approval_id
    raise TypeError("expected (scope, run_id, approval_id, approved) or legacy (run_id, approval_id, approved)")


def _failure_args(
    scope: TenantScope | str | None,
    run_id: str | None,
    message: str | None,
    *,
    tenant_id: str | None = None,
) -> tuple[TenantScope, str, str]:
    if isinstance(scope, TenantScope):
        if run_id is None or message is None:
            raise TypeError("run_id and message are required")
        _ensure_tenant_match(scope, tenant_id)
        return scope, run_id, message
    if isinstance(scope, str) and run_id is not None and message is None:
        return TenantScope.from_tenant_id(tenant_id), scope, run_id
    raise TypeError("expected (scope, run_id, message) or legacy (run_id, message)")


def _request_for_scope(scope: TenantScope, request: dict[str, Any]) -> dict[str, Any]:
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


def _raw_user_hash(raw_snapshot: Any) -> str | None:
    if isinstance(raw_snapshot, IdentitySnapshot):
        return raw_snapshot.user_hash
    if isinstance(raw_snapshot, dict) and "user_hash" in raw_snapshot:
        value = raw_snapshot.get("user_hash")
        return str(value) if value is not None else None
    return None


def _ensure_tenant_match(scope: TenantScope, tenant_id: str | None) -> None:
    if tenant_id is not None and tenant_id != scope.tenant_id:
        raise ValueError(f"tenant mismatch for scope: {tenant_id} != {scope.tenant_id}")

"""Persisted research-agent runtime adapter."""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator

from doge.application.agent.runtime_kernel import RuntimeKernel
from doge.core.domain.agent_models import AgentArtifact, AgentEvent, AgentRun
from doge.core.ports.agent_runtime import IResearchAgentRuntime
from doge.shared.scope import TenantScope


class PersistedResearchAgentRuntime(IResearchAgentRuntime):
    """Research runtime backed by repositories and the common runtime kernel."""

    def __init__(self, kernel: RuntimeKernel) -> None:
        self._kernel = kernel

    async def create_run(self, request: dict[str, Any], *, tenant_id: str | None = None) -> AgentRun:
        return await self._kernel.create_run(request, tenant_id=tenant_id)

    async def run_to_pause_or_completion(self, run_id: str, *, tenant_id: str | None = None) -> AgentRun:
        return await self._kernel.run_to_pause_or_completion(run_id, tenant_id=tenant_id)

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


def _run_args(
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


def _list_runs_args(
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
        return scope, run_id, message
    if isinstance(scope, str) and run_id is not None and message is None:
        return TenantScope.from_tenant_id(tenant_id), scope, run_id
    raise TypeError("expected (scope, run_id, message) or legacy (run_id, message)")

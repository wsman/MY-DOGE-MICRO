"""Persisted research-agent runtime adapter."""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator

from doge.application.agent.runtime_args import (
    approval_args as _approval_args,
    create_run_args as _create_run_args,
    failure_args as _failure_args,
    list_runs_args as _list_runs_args,
    queue_args as _queue_args,
    run_args as _run_args,
    run_execution_args as _run_execution_args,
)
from doge.application.agent.runtime_kernel import RuntimeKernel
from doge.core.domain.agent_models import AgentArtifact, AgentEvent, AgentRun
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
        resolved_scope, resolved_request = _create_run_args(scope, request, tenant_id=tenant_id)
        return await self._kernel.create_run(resolved_scope, resolved_request)

    async def run_to_pause_or_completion(
        self,
        scope: TenantScope | str | None,
        run_id: str | None = None,
        *,
        tenant_id: str | None = None,
    ) -> AgentRun:
        resolved_scope, resolved_run_id = _run_execution_args(scope, run_id, tenant_id=tenant_id)
        return await self._kernel.run_to_pause_or_completion(resolved_scope, resolved_run_id)

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

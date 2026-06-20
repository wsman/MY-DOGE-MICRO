"""Persisted research-agent runtime adapter."""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator

from doge.application.agent.runtime_kernel import RuntimeKernel
from doge.core.domain.agent_models import AgentArtifact, AgentEvent, AgentRun
from doge.core.ports.agent_runtime import IResearchAgentRuntime


class PersistedResearchAgentRuntime(IResearchAgentRuntime):
    """Research runtime backed by repositories and the common runtime kernel."""

    def __init__(self, kernel: RuntimeKernel) -> None:
        self._kernel = kernel

    async def create_run(self, request: dict[str, Any]) -> AgentRun:
        return await self._kernel.create_run(request)

    async def run_to_pause_or_completion(self, run_id: str) -> AgentRun:
        return await self._kernel.run_to_pause_or_completion(run_id)

    def get_run(self, run_id: str) -> AgentRun | None:
        return self._kernel.get_run(run_id)

    def list_runs(self, session_id: str | None = None, limit: int = 20) -> list[AgentRun]:
        return self._kernel.list_runs(session_id, limit)

    def list_events(self, run_id: str) -> list[AgentEvent]:
        return self._kernel.list_events(run_id)

    def list_artifacts(self, run_id: str) -> list[AgentArtifact]:
        return self._kernel.list_artifacts(run_id)

    async def stream_events(self, run_id: str) -> AsyncIterator[AgentEvent]:
        for event in self.list_events(run_id):
            yield event
            await asyncio.sleep(0)

    async def resolve_approval(self, run_id: str, approval_id: str, approved: bool) -> AgentRun:
        return await self._kernel.resolve_approval(run_id, approval_id, approved)

    async def cancel_run(self, run_id: str) -> AgentRun:
        return await self._kernel.cancel_run(run_id)

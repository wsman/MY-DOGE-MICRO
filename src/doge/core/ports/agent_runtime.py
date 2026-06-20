"""Research agent runtime port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

from doge.core.domain.agent_models import AgentArtifact, AgentEvent, AgentRun


class IResearchAgentRuntime(ABC):
    """Application-facing runtime interface for research-agent runs."""

    @abstractmethod
    async def create_run(self, request: dict[str, Any]) -> AgentRun:
        ...

    @abstractmethod
    async def run_to_pause_or_completion(self, run_id: str) -> AgentRun:
        ...

    @abstractmethod
    async def queue_run(self, run_id: str, reason: str = "queued") -> AgentRun:
        ...

    @abstractmethod
    def get_run(self, run_id: str) -> AgentRun | None:
        ...

    @abstractmethod
    def list_runs(self, session_id: str | None = None, limit: int = 20) -> list[AgentRun]:
        ...

    @abstractmethod
    def list_events(self, run_id: str) -> list[AgentEvent]:
        ...

    @abstractmethod
    def list_artifacts(self, run_id: str) -> list[AgentArtifact]:
        ...

    @abstractmethod
    async def stream_events(self, run_id: str) -> AsyncIterator[AgentEvent]:
        ...

    @abstractmethod
    async def resolve_approval(self, run_id: str, approval_id: str, approved: bool) -> AgentRun:
        ...

    @abstractmethod
    async def cancel_run(self, run_id: str) -> AgentRun:
        ...

    @abstractmethod
    async def finalize_cancelled(self, run_id: str) -> AgentRun:
        ...

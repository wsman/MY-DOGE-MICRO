"""Backend abstraction for agent model/runtime providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

from doge.core.ports.agent_model import AgentMessage, AgentResponse


class IAgentBackend(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: list[AgentMessage],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
        max_tokens: int = 16384,
        *,
        request_metadata: dict[str, Any] | None = None,
        prompt_cache_key: str | None = None,
        model: str | None = None,
    ) -> AsyncIterator[AgentResponse]:
        ...

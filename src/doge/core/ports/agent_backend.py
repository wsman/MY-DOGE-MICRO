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
    ) -> AsyncIterator[AgentResponse]:
        ...

"""Enterprise model gateway port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

from doge.core.domain.enterprise_context import EnterpriseCallContext
from doge.core.ports.agent_model import AgentMessage, AgentResponse


class IEnterpriseModelGateway(ABC):
    """Provider-neutral gateway for governed model calls."""

    @abstractmethod
    async def chat(
        self,
        context: EnterpriseCallContext,
        messages: list[AgentMessage],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = "auto",
        stream: bool = True,
    ) -> AsyncIterator[AgentResponse]:
        ...

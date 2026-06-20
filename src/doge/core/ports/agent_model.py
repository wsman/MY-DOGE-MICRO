"""Agent-capable model port.

This port is separate from ``ILLMClient`` on purpose. Text-only report
generation keeps the narrow synchronous contract, while agent workflows need
multimodal messages, tool calls, reasoning content, usage, and streaming.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional


@dataclass(frozen=True)
class AgentMessage:
    """OpenAI-compatible chat message with Kimi reasoning/tool extensions."""

    role: str
    content: Any = ""
    reasoning_content: Optional[str] = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tool_call_id: Optional[str] = None
    name: Optional[str] = None

    def to_api_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.reasoning_content:
            data["reasoning_content"] = self.reasoning_content
        if self.tool_calls:
            data["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            data["tool_call_id"] = self.tool_call_id
        if self.name:
            data["name"] = self.name
        return data


@dataclass(frozen=True)
class AgentResponse:
    """Single model event/chunk returned by an agent model."""

    message: AgentMessage
    finish_reason: Optional[str] = None
    usage: Optional[dict[str, Any]] = None
    raw: Optional[dict[str, Any]] = None


class IAgentModel(ABC):
    """Async streaming model interface for agent runtimes."""

    @abstractmethod
    async def chat(
        self,
        messages: list[AgentMessage],
        *,
        tools: Optional[list[dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        max_tokens: int = 16384,
        stream: bool = True,
    ) -> AsyncIterator[AgentResponse]:
        """Yield model response events for an agent turn."""
        ...

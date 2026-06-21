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
class AgentContentPart:
    """Provider-neutral structured content part for multimodal messages."""

    type: str
    text: Optional[str] = None
    source_type: Optional[str] = None
    media_type: Optional[str] = None
    data: Optional[str] = None
    file_id: Optional[str] = None
    filename: Optional[str] = None

    @classmethod
    def text_part(cls, text: str) -> "AgentContentPart":
        return cls(type="text", text=text)

    @classmethod
    def image_base64(cls, *, media_type: str, data: str) -> "AgentContentPart":
        return cls(type="image", source_type="base64", media_type=media_type, data=data)

    @classmethod
    def image_file_id(cls, file_id: str) -> "AgentContentPart":
        return cls(type="image", source_type="file_id", file_id=file_id)

    @classmethod
    def file_text(cls, *, text: str, filename: str | None = None, file_id: str | None = None) -> "AgentContentPart":
        return cls(type="file_text", text=text, filename=filename, file_id=file_id)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"type": self.type}
        if self.text is not None:
            data["text"] = self.text
        if self.source_type:
            data["source"] = {
                key: value
                for key, value in {
                    "type": self.source_type,
                    "media_type": self.media_type,
                    "data": self.data,
                    "file_id": self.file_id,
                }.items()
                if value is not None
            }
        if self.filename:
            data["filename"] = self.filename
        if self.file_id and self.type == "file_text":
            data["file_id"] = self.file_id
        return data


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
        data: dict[str, Any] = {"role": self.role, "content": _serialize_content(self.content)}
        if self.reasoning_content:
            data["reasoning_content"] = self.reasoning_content
        if self.tool_calls:
            data["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            data["tool_call_id"] = self.tool_call_id
        if self.name:
            data["name"] = self.name
        return data


def _serialize_content(content: Any) -> Any:
    if isinstance(content, AgentContentPart):
        return content.to_dict()
    if isinstance(content, list):
        return [_serialize_content(item) for item in content]
    if isinstance(content, tuple):
        return [_serialize_content(item) for item in content]
    return content


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

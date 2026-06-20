"""Agent backend adapters."""

from __future__ import annotations

from typing import Any, AsyncIterator

from doge.core.ports.agent_backend import IAgentBackend
from doge.core.ports.agent_model import AgentMessage, AgentResponse
from doge.infrastructure.agent.scripted_model import ScriptedAgentModel
from doge.infrastructure.llm.kimi_client import KimiAgentModel


class DirectKimiApiBackend(IAgentBackend):
    """Backend that delegates directly to the OpenAI-compatible Kimi adapter."""

    def __init__(self, model: KimiAgentModel | None = None) -> None:
        self._model = model or KimiAgentModel()

    async def chat(
        self,
        messages: list[AgentMessage],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
        max_tokens: int = 16384,
    ) -> AsyncIterator[AgentResponse]:
        async for response in self._model.chat(
            messages,
            tools=tools,
            tool_choice=tool_choice,
            max_tokens=max_tokens,
            stream=True,
        ):
            yield response


class ScriptedDemoBackend(IAgentBackend):
    """Deterministic backend for offline demos and contract tests."""

    def __init__(self, model: ScriptedAgentModel | None = None) -> None:
        self._model = model or ScriptedAgentModel()

    async def chat(
        self,
        messages: list[AgentMessage],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
        max_tokens: int = 16384,
    ) -> AsyncIterator[AgentResponse]:
        async for response in self._model.chat(
            messages,
            tools=tools,
            tool_choice=tool_choice,
            max_tokens=max_tokens,
            stream=True,
        ):
            yield response


class KimiAgentSdkBackend(IAgentBackend):
    """Reserved adapter boundary for the Kimi Agent SDK."""

    async def chat(
        self,
        messages: list[AgentMessage],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
        max_tokens: int = 16384,
    ) -> AsyncIterator[AgentResponse]:
        if False:
            yield AgentResponse(message=AgentMessage(role="assistant", content=""))
        raise NotImplementedError("Kimi Agent SDK backend is reserved for a future optional epic")

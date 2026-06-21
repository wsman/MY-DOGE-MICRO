"""Agent backend adapters."""

from __future__ import annotations

import importlib
from typing import Any, AsyncIterator

from doge.core.ports.agent_backend import IAgentBackend
from doge.core.ports.agent_model import AgentMessage, AgentResponse
from doge.infrastructure.agent.kimi_sdk_adapter import KimiSdkEventAdapter
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
    """Optional backend that delegates to the Kimi Agent SDK prompt API."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        config: Any | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self._config = config
        self._adapter = KimiSdkEventAdapter()

    async def chat(
        self,
        messages: list[AgentMessage],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
        max_tokens: int = 16384,
    ) -> AsyncIterator[AgentResponse]:
        sdk = _load_kimi_agent_sdk()
        prompt = getattr(sdk, "prompt")
        config = self._config or _build_sdk_config(sdk, self._api_key, self._base_url, self._model)
        async for message in prompt(self._adapter.messages_to_prompt(messages), config=config, yolo=False):
            yield self._adapter.to_response(message)


def _load_kimi_agent_sdk():
    try:
        return importlib.import_module("kimi_agent_sdk")
    except ImportError as exc:
        raise ImportError(
            "kimi-agent-sdk is not installed; install it to use KimiAgentSdkBackend"
        ) from exc


def _build_sdk_config(sdk, api_key: str | None, base_url: str | None, model: str | None):
    if not any([api_key, base_url, model]) or not hasattr(sdk, "Config"):
        return None
    model_name = model or "kimi-k2-thinking-turbo"
    return sdk.Config(
        default_model=model_name,
        providers={
            "kimi": {
                "type": "kimi",
                "base_url": base_url,
                "api_key": api_key,
            }
        },
        models={model_name: {"provider": "kimi", "model": model_name}},
    )


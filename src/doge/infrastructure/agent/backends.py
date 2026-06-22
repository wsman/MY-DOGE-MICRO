"""Agent backend adapters."""

from __future__ import annotations

import importlib
import inspect
from typing import Any, AsyncIterator

from doge.core.ports.agent_backend import IAgentBackend
from doge.core.ports.agent_model import AgentMessage, AgentResponse
from doge.core.ports.secrets import ISecretProvider
from doge.infrastructure.agent.kimi_sdk_adapter import KimiSdkEventAdapter
from doge.infrastructure.agent.scripted_model import ScriptedAgentModel
from doge.infrastructure.llm.kimi_client import KimiAgentModel
from doge.infrastructure.secrets import EnvSecretProvider


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
        *,
        request_metadata: dict[str, Any] | None = None,
        prompt_cache_key: str | None = None,
        model: str | None = None,
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
        *,
        request_metadata: dict[str, Any] | None = None,
        prompt_cache_key: str | None = None,
        model: str | None = None,
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
        secret_provider: ISecretProvider | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self._config = config
        self._secret_provider = secret_provider or EnvSecretProvider()
        self._adapter = KimiSdkEventAdapter()

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
        sdk = _load_kimi_agent_sdk()
        prompt = getattr(sdk, "prompt")
        model_name = model or self._model
        api_key = self._api_key if self._api_key is not None else self._secret_provider.get_secret("kimi.api_key")
        config = self._config or _build_sdk_config(sdk, api_key, self._base_url, model_name)
        request = self._adapter.build_prompt_request(
            messages,
            tools=tools,
            tool_choice=tool_choice,
            max_tokens=max_tokens,
            request_metadata=request_metadata,
            prompt_cache_key=prompt_cache_key,
            model=model_name,
        )
        kwargs = _supported_prompt_kwargs(prompt, {
            "config": config,
            "yolo": False,
            **self._adapter.to_prompt_kwargs(request),
        })
        async for message in prompt(request.prompt, **kwargs):
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


def _supported_prompt_kwargs(prompt, kwargs: dict[str, Any]) -> dict[str, Any]:
    try:
        signature = inspect.signature(prompt)
    except (TypeError, ValueError):
        return kwargs
    parameters = signature.parameters
    if any(parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in parameters.values()):
        return kwargs
    accepted = {
        name for name, parameter in parameters.items()
        if name != "prompt" and parameter.kind in {
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        }
    }
    return {key: value for key, value in kwargs.items() if key in accepted}

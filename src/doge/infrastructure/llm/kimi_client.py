"""Kimi agent model adapter."""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Optional

from doge.config import get_settings
from doge.core.ports.agent_model import AgentMessage, AgentResponse, IAgentModel

logger = logging.getLogger(__name__)


class KimiAgentModel(IAgentModel):
    """OpenAI-compatible async adapter for Kimi K2 models."""

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        settings = get_settings().kimi
        self._api_key = api_key if api_key is not None else settings.api_key
        self._base_url = base_url if base_url is not None else settings.base_url
        self._model = model if model is not None else settings.general_model

    async def chat(
        self,
        messages: list[AgentMessage],
        *,
        tools: Optional[list[dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        max_tokens: int = 16384,
        stream: bool = True,
    ) -> AsyncIterator[AgentResponse]:
        """Yield Kimi chat events.

        Kimi K2.6 thinking + tool calling only accepts ``auto`` or ``none`` for
        ``tool_choice``. Temperature is intentionally not exposed or passed.
        """
        if tools and tool_choice not in (None, "auto", "none"):
            raise ValueError("Kimi thinking tool calls require tool_choice auto or none")
        if not self._api_key:
            logger.warning("Kimi API key not configured")
            return

        try:
            from openai import AsyncOpenAI
        except ImportError:  # pragma: no cover - dependency is installed in normal envs
            logger.warning("openai package not installed")
            return

        client = AsyncOpenAI(api_key=self._api_key, base_url=self._base_url)
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": [message.to_api_dict() for message in messages],
            "max_tokens": max_tokens,
            "stream": stream,
        }
        if not self._model.startswith("kimi-k2.7-code"):
            kwargs["extra_body"] = {"thinking": {"type": "enabled", "keep": "all"}}
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice or "auto"

        try:
            response = await client.chat.completions.create(**kwargs)
        except Exception as exc:  # noqa: BLE001 - degrade like DeepSeekClient
            logger.warning("Kimi chat request failed: %s", exc)
            return

        if stream:
            async for chunk in response:
                if not chunk.choices:
                    continue
                choice = chunk.choices[0]
                delta = choice.delta
                yield AgentResponse(
                    message=AgentMessage(
                        role=getattr(delta, "role", None) or "assistant",
                        content=getattr(delta, "content", None) or "",
                        reasoning_content=getattr(delta, "reasoning_content", None),
                        tool_calls=[tc.model_dump(exclude_none=True) for tc in (getattr(delta, "tool_calls", None) or [])],
                    ),
                    finish_reason=choice.finish_reason,
                    raw=chunk.model_dump(exclude_none=True),
                )
            return

        message = response.choices[0].message
        yield AgentResponse(
            message=AgentMessage(
                role=message.role,
                content=message.content or "",
                reasoning_content=getattr(message, "reasoning_content", None),
                tool_calls=[tc.model_dump(exclude_none=True) for tc in (message.tool_calls or [])],
            ),
            finish_reason=response.choices[0].finish_reason,
            usage=response.usage.model_dump(exclude_none=True) if response.usage else None,
            raw=response.model_dump(exclude_none=True),
        )

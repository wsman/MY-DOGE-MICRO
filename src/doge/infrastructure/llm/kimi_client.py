"""Kimi agent model adapter."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterator, Awaitable, Callable, Optional

from doge.config import get_settings
from doge.core.ports.agent_model import AgentMessage, AgentResponse, IAgentModel

logger = logging.getLogger(__name__)


class KimiMessageSerializer:
    """Translate provider-neutral agent messages into Kimi chat payloads."""

    @classmethod
    def serialize_messages(cls, messages: list[AgentMessage]) -> list[dict[str, Any]]:
        payload: list[dict[str, Any]] = []
        for message in messages:
            payload.extend(cls.serialize_message(message))
        return payload

    @classmethod
    def serialize_message(cls, message: AgentMessage) -> list[dict[str, Any]]:
        data = message.to_api_dict()
        content = data.get("content")
        if not isinstance(content, list):
            return [data]

        file_messages: list[dict[str, Any]] = []
        content_parts: list[dict[str, Any]] = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "file_text":
                file_content = part.get("text") or ""
                if file_content:
                    file_messages.append({"role": "system", "content": file_content})
                continue
            content_parts.append(cls.serialize_content_part(part))

        if content_parts:
            data["content"] = content_parts
            return [*file_messages, data]
        if file_messages:
            return file_messages
        data["content"] = []
        return [data]

    @classmethod
    def serialize_content_part(cls, part: Any) -> Any:
        if not isinstance(part, dict):
            return part
        if part.get("type") == "text":
            return {"type": "text", "text": part.get("text", "")}
        if part.get("type") == "image":
            return {
                "type": "image_url",
                "image_url": {"url": cls._image_url(part)},
            }
        if part.get("type") in {"image_url", "video_url"}:
            return part
        return part

    @staticmethod
    def _image_url(part: dict[str, Any]) -> str:
        source = part.get("source") or {}
        if source.get("type") == "file_id":
            return f"ms://{source.get('file_id', '')}"
        if source.get("type") == "base64":
            media_type = source.get("media_type") or "image/png"
            return f"data:{media_type};base64,{source.get('data', '')}"
        return part.get("image_url") or ""


class KimiAgentModel(IAgentModel):
    """OpenAI-compatible async adapter for Kimi K2 models."""

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: int | None = None,
        retry_delay: float | None = None,
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        settings = get_settings().kimi
        self._api_key = api_key if api_key is not None else settings.api_key
        self._base_url = base_url if base_url is not None else settings.base_url
        self._model = model if model is not None else settings.general_model
        self._max_retries = max(0, max_retries if max_retries is not None else settings.max_retries)
        self._retry_delay = retry_delay if retry_delay is not None else settings.retry_delay
        self._sleep = sleep or asyncio.sleep

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
            "messages": KimiMessageSerializer.serialize_messages(messages),
            "max_tokens": max_tokens,
            "stream": stream,
        }
        if not self._model.startswith("kimi-k2.7-code"):
            kwargs["extra_body"] = {"thinking": {"type": "enabled", "keep": "all"}}
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice or "auto"

        response = await self._create_completion_with_retry(client.chat.completions, kwargs)
        if response is None:
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

    async def _create_completion_with_retry(self, completions: Any, kwargs: dict[str, Any]) -> Any | None:
        for attempt in range(self._max_retries + 1):
            try:
                return await completions.create(**kwargs)
            except Exception as exc:  # noqa: BLE001 - provider exceptions vary by transport/client version
                if attempt >= self._max_retries or not _is_retryable_kimi_error(exc):
                    logger.warning("Kimi chat request failed: %s", exc)
                    return None
                logger.warning(
                    "Kimi chat retry %d/%d after provider error: %s",
                    attempt + 1,
                    self._max_retries,
                    exc,
                )
                if self._retry_delay > 0:
                    await self._sleep(self._retry_delay)
        return None


def _is_retryable_kimi_error(error: BaseException) -> bool:
    message = str(error).lower()
    retry_tokens = (
        "429",
        "rate",
        "too many requests",
        "timeout",
        "temporar",
        "connection",
        "service unavailable",
        "server error",
        "5xx",
    )
    return any(token in message for token in retry_tokens)

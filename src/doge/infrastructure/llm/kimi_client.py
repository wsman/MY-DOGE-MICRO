"""Kimi agent model adapter."""

from __future__ import annotations

import asyncio
import logging
import random
from time import perf_counter
from typing import Any, AsyncIterator, Awaitable, Callable, Optional

from doge.config import get_settings
from doge.core.ports.secrets import ISecretProvider
from doge.infrastructure.secrets import EnvSecretProvider
from doge.core.ports.agent_model import AgentMessage, AgentResponse, AgentUsage, IAgentModel
from doge.infrastructure.llm.cost_calculator import CostCalculator

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
        if part.get("type") == "video":
            return {
                "type": "video_url",
                "video_url": {"url": cls._image_url(part)},
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
        timeout: float | None = None,
        backoff_base: float | None = None,
        backoff_max: float | None = None,
        cost_calculator: CostCalculator | None = None,
        secret_provider: ISecretProvider | None = None,
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        settings = get_settings().kimi
        secrets = secret_provider or EnvSecretProvider()
        self._api_key = api_key if api_key is not None else (secrets.get_secret("kimi.api_key") or settings.api_key)
        self._base_url = base_url if base_url is not None else settings.effective_base_url()
        self._default_headers = settings.default_http_headers()
        self._model = model if model is not None else settings.general_model
        self._max_retries = max(0, max_retries if max_retries is not None else settings.max_retries)
        self._retry_delay = retry_delay if retry_delay is not None else settings.retry_delay
        self._timeout = timeout if timeout is not None else settings.timeout_seconds
        self._backoff_base = backoff_base if backoff_base is not None else settings.backoff_base_seconds
        self._backoff_max = backoff_max if backoff_max is not None else settings.backoff_max_seconds
        self._cost_calculator = cost_calculator or CostCalculator()
        self._sleep = sleep or asyncio.sleep

    async def chat(
        self,
        messages: list[AgentMessage],
        *,
        tools: Optional[list[dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        max_tokens: int = 16384,
        max_completion_tokens: Optional[int] = None,
        stream: bool = True,
        model: Optional[str] = None,
        thinking_enabled: Optional[bool] = None,
        response_format: Optional[dict[str, Any]] = None,
        prompt_cache_key: Optional[str] = None,
        safety_identifier: Optional[str] = None,
        timeout: Optional[float] = None,
        request_metadata: Optional[dict[str, Any]] = None,
        extra_body: Optional[dict[str, Any]] = None,
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
        request_model = model or self._model
        if request_model.startswith("kimi-k2.7-code") and thinking_enabled is False:
            raise ValueError(
                "kimi-k2.7-code does not support thinking_enabled=False; "
                "thinking must remain enabled or omitted"
            )

        try:
            from openai import AsyncOpenAI
        except ImportError:  # pragma: no cover - dependency is installed in normal envs
            logger.warning("openai package not installed")
            return

        client = AsyncOpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
            timeout=timeout or self._timeout,
            default_headers=self._default_headers or None,
        )
        kwargs: dict[str, Any] = {
            "model": request_model,
            "messages": KimiMessageSerializer.serialize_messages(messages),
            "max_completion_tokens": max_completion_tokens or max_tokens,
            "stream": stream,
        }
        if response_format:
            kwargs["response_format"] = response_format
        if prompt_cache_key:
            kwargs["prompt_cache_key"] = prompt_cache_key
        if safety_identifier:
            kwargs["safety_identifier"] = safety_identifier
        resolved_extra_body = _build_extra_body(
            request_model=request_model,
            thinking_enabled=thinking_enabled,
            extra_body=extra_body,
        )
        if resolved_extra_body:
            kwargs["extra_body"] = resolved_extra_body
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice or "auto"

        started = perf_counter()
        response = await self._create_completion_with_retry(client.chat.completions, kwargs)
        if response is None:
            return
        latency_ms = (perf_counter() - started) * 1000

        if stream:
            async for chunk in response:
                choices = getattr(chunk, "choices", None) or []
                if not choices:
                    continue
                choice = choices[0]
                delta = getattr(choice, "delta", None)
                chunk_usage = _usage_from_obj(getattr(chunk, "usage", None) or getattr(choice, "usage", None))
                yield AgentResponse(
                    message=AgentMessage(
                        role=getattr(delta, "role", None) or "assistant",
                        content=getattr(delta, "content", None) or "",
                        reasoning_content=getattr(delta, "reasoning_content", None),
                        tool_calls=[_dump_tool_call(tc) for tc in (getattr(delta, "tool_calls", None) or [])],
                    ),
                    finish_reason=choice.finish_reason,
                    usage=self._usage_payload(
                        chunk_usage,
                        model=getattr(chunk, "model", None) or request_model,
                        provider_request_id=getattr(chunk, "id", None),
                        latency_ms=latency_ms if choice.finish_reason else None,
                        request_metadata=request_metadata,
                    ) if chunk_usage else None,
                    raw=_model_dump(chunk),
                )
            return

        message = response.choices[0].message
        usage = _usage_from_obj(response.usage)
        yield AgentResponse(
            message=AgentMessage(
                role=message.role,
                content=message.content or "",
                reasoning_content=getattr(message, "reasoning_content", None),
                tool_calls=[_dump_tool_call(tc) for tc in (message.tool_calls or [])],
            ),
            finish_reason=response.choices[0].finish_reason,
            usage=self._usage_payload(
                usage,
                model=getattr(response, "model", None) or request_model,
                provider_request_id=getattr(response, "id", None),
                latency_ms=latency_ms,
                request_metadata=request_metadata,
            ) if usage else None,
            raw=_model_dump(response),
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
                delay = self._retry_delay if self._retry_delay is not None else self._backoff_base
                delay = min(delay * (2 ** attempt), self._backoff_max)
                delay = delay + random.uniform(0, delay * 0.1) if delay > 0 else 0
                if delay > 0:
                    await self._sleep(delay)
        return None

    def _usage_payload(
        self,
        usage: dict[str, Any],
        *,
        model: str | None,
        provider_request_id: str | None,
        latency_ms: float | None,
        request_metadata: dict[str, Any] | None,
    ) -> dict[str, Any]:
        normalized = AgentUsage.from_mapping(
            usage,
            model=model,
            provider_request_id=provider_request_id,
            latency_ms=latency_ms,
        )
        cost = self._cost_calculator.calculate_cost(
            model=normalized.model,
            prompt_tokens=normalized.prompt_tokens,
            completion_tokens=normalized.completion_tokens,
            cached_tokens=normalized.cached_tokens,
        )
        payload = AgentUsage.from_mapping(
            normalized.to_dict(),
            model=normalized.model,
            provider_request_id=normalized.provider_request_id,
            latency_ms=normalized.latency_ms,
            cost_usd=cost,
        ).to_dict()
        if request_metadata:
            payload["request_metadata"] = request_metadata
        return payload


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


def _build_extra_body(
    *,
    request_model: str,
    thinking_enabled: bool | None,
    extra_body: dict[str, Any] | None,
) -> dict[str, Any]:
    resolved: dict[str, Any] = {}
    is_k27 = request_model.startswith("kimi-k2.7-code")
    if is_k27 and thinking_enabled is True:
        resolved["thinking"] = {"type": "enabled", "keep": "all"}
    elif not is_k27 and thinking_enabled is True:
        resolved["thinking"] = {"type": "enabled", "keep": "all"}
    elif not is_k27 and thinking_enabled is False:
        resolved["thinking"] = {"type": "disabled"}
    elif thinking_enabled is None and not is_k27:
        resolved["thinking"] = {"type": "enabled", "keep": "all"}
    if extra_body:
        resolved.update(extra_body)
    return resolved


def _usage_from_obj(usage: Any) -> dict[str, Any]:
    if usage is None:
        return {}
    if isinstance(usage, dict):
        return dict(usage)
    if hasattr(usage, "model_dump"):
        return usage.model_dump(exclude_none=True)
    return dict(getattr(usage, "__dict__", {}) or {})


def _model_dump(obj: Any) -> dict[str, Any]:
    if hasattr(obj, "model_dump"):
        return obj.model_dump(exclude_none=True)
    return dict(getattr(obj, "__dict__", {}) or {})


def _dump_tool_call(tool_call: Any) -> dict[str, Any]:
    if hasattr(tool_call, "model_dump"):
        return tool_call.model_dump(exclude_none=True)
    if isinstance(tool_call, dict):
        return dict(tool_call)
    return dict(getattr(tool_call, "__dict__", {}) or {})

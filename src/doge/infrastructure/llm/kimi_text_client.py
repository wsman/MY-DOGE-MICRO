"""Kimi-backed adapter for the narrow text-only LLM port."""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from doge.config import get_settings
from doge.core.ports.agent_model import AgentMessage
from doge.core.ports.llm import ILLMClient
from doge.infrastructure.llm.kimi_client import KimiAgentModel

logger = logging.getLogger(__name__)


class KimiTextClient(ILLMClient):
    """Synchronous ``ILLMClient`` facade over the async Kimi agent adapter."""

    def __init__(self, model: KimiAgentModel | None = None) -> None:
        self._agent_model = model or KimiAgentModel()

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> Optional[str]:
        """Return a text completion or ``None`` on degraded provider failure."""

        try:
            return _run_sync(self._chat_async(system_prompt, user_prompt, max_tokens=max_tokens))
        except Exception as exc:  # noqa: BLE001 - mirrors DeepSeekClient degraded contract
            logger.warning("Kimi text chat request failed: %s", exc)
            return None

    async def _chat_async(self, system_prompt: str, user_prompt: str, *, max_tokens: int) -> Optional[str]:
        settings = get_settings()
        content_parts: list[str] = []
        async for response in self._agent_model.chat(
            [
                AgentMessage(role="system", content=system_prompt),
                AgentMessage(role="user", content=user_prompt),
            ],
            model=settings.kimi.general_model,
            max_completion_tokens=max_tokens,
            stream=False,
            thinking_enabled=True,
            request_metadata={"adapter": "KimiTextClient"},
        ):
            if response.message.content:
                content_parts.append(str(response.message.content))
        return "".join(content_parts) or None


def _run_sync(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(lambda: asyncio.run(coro)).result()

"""Kimi-backed enterprise model gateway."""

from __future__ import annotations

from typing import Any, AsyncIterator

from doge.config import get_settings
from doge.core.domain.enterprise_context import EnterpriseCallContext
from doge.core.ports.agent_model import AgentMessage, AgentResponse, IAgentModel
from doge.core.ports.model_gateway import IEnterpriseModelGateway
from doge.infrastructure.llm.kimi_client import KimiAgentModel

_CODE_TASKS = {"python", "sql", "backtest", "data_pipeline"}


class KimiEnterpriseGateway(IEnterpriseModelGateway):
    """Apply OpenDoge enterprise call metadata to Kimi chat requests."""

    def __init__(self, model: IAgentModel | None = None) -> None:
        self._settings = get_settings()
        self._model = model or KimiAgentModel()

    async def chat(
        self,
        context: EnterpriseCallContext,
        messages: list[AgentMessage],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = "auto",
        stream: bool = True,
    ) -> AsyncIterator[AgentResponse]:
        response_format = None
        if context.response_schema:
            response_format = {
                "type": "json_schema",
                "json_schema": context.response_schema,
            }
        async for event in self._model.chat(
            messages,
            tools=tools,
            tool_choice=tool_choice,
            model=self.select_model(context.task_type),
            max_completion_tokens=self._settings.kimi.max_completion_tokens,
            stream=stream,
            response_format=response_format,
            prompt_cache_key=context.session_id if self._settings.kimi.prompt_cache_enabled else None,
            safety_identifier=context.user_hash,
            timeout=self._settings.kimi.timeout_seconds,
            request_metadata={
                "tenant_id": context.tenant_id,
                "session_id": context.session_id,
                "task_type": context.task_type,
            },
        ):
            yield event

    def select_model(self, task_type: str) -> str:
        if task_type in _CODE_TASKS:
            return self._settings.kimi.code_model
        return self._settings.kimi.general_model

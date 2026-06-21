from typing import Any, AsyncIterator

import pytest

from doge.config import reset_settings
from doge.core.domain.enterprise_context import EnterpriseCallContext
from doge.core.ports.agent_model import AgentMessage, AgentResponse
from doge.infrastructure.llm.kimi_enterprise_gateway import KimiEnterpriseGateway


class CapturingModel:
    def __init__(self):
        self.kwargs: dict[str, Any] = {}

    async def chat(self, messages, **kwargs) -> AsyncIterator[AgentResponse]:
        self.kwargs = kwargs
        yield AgentResponse(message=AgentMessage(role="assistant", content="ok"))


@pytest.mark.asyncio
async def test_kimi_enterprise_gateway_adds_enterprise_request_fields(monkeypatch):
    monkeypatch.setenv("KIMI_GENERAL_MODEL", "kimi-k2.6")
    monkeypatch.setenv("KIMI_CODE_MODEL", "kimi-k2.7-code")
    monkeypatch.setenv("KIMI_PROMPT_CACHE_ENABLED", "true")
    reset_settings()
    model = CapturingModel()
    gateway = KimiEnterpriseGateway(model=model)

    responses = [
        response
        async for response in gateway.chat(
            EnterpriseCallContext(
                tenant_id="tenant-a",
                user_hash="user-hash",
                session_id="ses-1",
                task_type="python",
                response_schema={"name": "memo", "schema": {"type": "object"}},
            ),
            [AgentMessage(role="user", content="analyze")],
        )
    ]

    assert responses[0].message.content == "ok"
    assert model.kwargs["model"] == "kimi-k2.7-code"
    assert model.kwargs["prompt_cache_key"] == "ses-1"
    assert model.kwargs["safety_identifier"] == "user-hash"
    assert model.kwargs["response_format"]["type"] == "json_schema"
    assert model.kwargs["request_metadata"]["tenant_id"] == "tenant-a"
    reset_settings()

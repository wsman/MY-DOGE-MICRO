from types import SimpleNamespace

import pytest

from doge.config.settings import reset_settings
from doge.core.ports.agent_model import AgentMessage
from doge.infrastructure.llm.kimi_client import KimiAgentModel


@pytest.mark.asyncio
async def test_kimi_client_yields_nothing_without_api_key(monkeypatch):
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    reset_settings()

    events = [event async for event in KimiAgentModel().chat([AgentMessage(role="user", content="hi")])]

    assert events == []


@pytest.mark.asyncio
async def test_kimi_client_rejects_non_auto_tool_choice():
    with pytest.raises(ValueError):
        _ = [
            event
            async for event in KimiAgentModel(api_key="key").chat(
                [AgentMessage(role="user", content="hi")],
                tools=[{"type": "function", "function": {"name": "abc", "parameters": {"type": "object"}}}],
                tool_choice="required",
            )
        ]


@pytest.mark.asyncio
async def test_kimi_client_omits_temperature_and_sets_thinking(monkeypatch):
    captured = {}

    class FakeCompletions:
        async def create(self, **kwargs):
            captured.update(kwargs)
            message = SimpleNamespace(
                role="assistant",
                content="memo",
                tool_calls=[],
            )
            choice = SimpleNamespace(message=message, finish_reason="stop")
            usage = SimpleNamespace(model_dump=lambda exclude_none=True: {"total_tokens": 7})
            return SimpleNamespace(
                choices=[choice],
                usage=usage,
                model_dump=lambda exclude_none=True: {"id": "resp-1"},
            )

    class FakeAsyncOpenAI:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.chat = SimpleNamespace(completions=FakeCompletions())

    import openai

    monkeypatch.setattr(openai, "AsyncOpenAI", FakeAsyncOpenAI)

    events = [
        event
        async for event in KimiAgentModel(
            api_key="moonshot-key",
            base_url="https://api.moonshot.ai/v1",
            model="kimi-k2.6",
        ).chat([AgentMessage(role="user", content="hi")], stream=False)
    ]

    assert len(events) == 1
    assert events[0].message.content == "memo"
    assert captured["client"]["api_key"] == "moonshot-key"
    assert captured["client"]["base_url"] == "https://api.moonshot.ai/v1"
    assert captured["model"] == "kimi-k2.6"
    assert "temperature" not in captured
    assert captured["extra_body"] == {"thinking": {"type": "enabled", "keep": "all"}}

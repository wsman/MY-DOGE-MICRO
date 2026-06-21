import sys
from types import SimpleNamespace

import pytest

from doge.core.ports.agent_model import AgentMessage
from doge.infrastructure.agent.backends import DirectKimiApiBackend, KimiAgentSdkBackend, ScriptedDemoBackend


@pytest.mark.asyncio
async def test_scripted_backend_deterministic_turns():
    backend = ScriptedDemoBackend()

    responses = [
        response
        async for response in backend.chat([AgentMessage(role="user", content="Analyze")], tools=[], tool_choice="auto")
    ]

    assert responses[0].message.tool_calls[0]["function"]["name"] == "stock_overview"


def test_direct_kimi_backend_api_contract():
    backend = DirectKimiApiBackend()

    assert backend is not None


@pytest.mark.asyncio
async def test_kimi_agent_sdk_backend_requires_optional_dependency(monkeypatch):
    monkeypatch.setitem(sys.modules, "kimi_agent_sdk", None)
    backend = KimiAgentSdkBackend()

    with pytest.raises(ImportError, match="kimi-agent-sdk is not installed"):
        responses = backend.chat([AgentMessage(role="user", content="Analyze")])
        await responses.__anext__()


@pytest.mark.asyncio
async def test_kimi_agent_sdk_backend_maps_prompt_stream(monkeypatch):
    captured = {}

    class FakeMessage:
        def __init__(self, text):
            self.text = text

        def extract_text(self):
            return self.text

    async def fake_prompt(prompt, **kwargs):
        captured["prompt"] = prompt
        captured["kwargs"] = kwargs
        yield FakeMessage("hello")

    fake_sdk = SimpleNamespace(prompt=fake_prompt)
    monkeypatch.setitem(sys.modules, "kimi_agent_sdk", fake_sdk)
    backend = KimiAgentSdkBackend()

    responses = [
        response
        async for response in backend.chat([AgentMessage(role="user", content="Analyze")])
    ]

    assert captured["prompt"] == "user: Analyze"
    assert captured["kwargs"]["yolo"] is False
    assert responses[0].message.content == "hello"


@pytest.mark.asyncio
async def test_kimi_agent_sdk_backend_maps_approval_request_to_existing_tool(monkeypatch):
    class FakeApprovalRequest:
        def __init__(self):
            self.id = "appr-sdk"
            self.action = "publish"

    async def fake_prompt(prompt, **kwargs):
        yield FakeApprovalRequest()

    fake_sdk = SimpleNamespace(prompt=fake_prompt)
    monkeypatch.setitem(sys.modules, "kimi_agent_sdk", fake_sdk)
    backend = KimiAgentSdkBackend()

    responses = [
        response
        async for response in backend.chat([AgentMessage(role="user", content="Analyze")])
    ]

    tool_call = responses[0].message.tool_calls[0]
    assert tool_call["function"]["name"] == "request_approval"
    assert '"risk_level": "high"' in tool_call["function"]["arguments"]

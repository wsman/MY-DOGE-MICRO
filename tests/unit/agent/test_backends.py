import sys
from types import SimpleNamespace

import pytest

from doge.core.ports.agent_model import AgentContentPart, AgentMessage
from doge.infrastructure.agent.backends import DirectKimiApiBackend, KimiAgentSdkBackend, ScriptedDemoBackend


class _SecretProvider:
    def __init__(self, values):
        self.values = values

    def get_secret(self, name: str):
        return self.values.get(name)


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
async def test_kimi_agent_sdk_backend_passes_structured_messages_tools_and_metadata(monkeypatch):
    captured = {}

    class FakeMessage:
        def extract_text(self):
            return "done"

    async def fake_prompt(prompt, **kwargs):
        captured["prompt"] = prompt
        captured["kwargs"] = kwargs
        yield FakeMessage()

    fake_sdk = SimpleNamespace(prompt=fake_prompt)
    monkeypatch.setitem(sys.modules, "kimi_agent_sdk", fake_sdk)
    backend = KimiAgentSdkBackend(model="kimi-k2.6")
    tools = [{
        "type": "function",
        "function": {
            "name": "lookup_evidence",
            "parameters": {"type": "object", "properties": {}},
        },
    }]

    responses = [
        response
        async for response in backend.chat(
            [
                AgentMessage(
                    role="user",
                    content=[
                        AgentContentPart.text_part("Analyze this chart."),
                        AgentContentPart.image_file_id("file-image-1"),
                    ],
                )
            ],
            tools=tools,
            tool_choice="auto",
            max_tokens=2048,
            request_metadata={
                "run_id": "run-1",
                "session_id": "ses-1",
                "execution_profile": "agent_automation",
            },
            prompt_cache_key="ses-1",
        )
    ]

    assert responses[0].message.content == "done"
    assert captured["prompt"].startswith("user:")
    assert captured["kwargs"]["messages"][0]["content"][1]["source"]["file_id"] == "file-image-1"
    assert captured["kwargs"]["tools"] == tools
    assert captured["kwargs"]["tool_choice"] == "auto"
    assert captured["kwargs"]["max_tokens"] == 2048
    assert captured["kwargs"]["session_id"] == "ses-1"
    assert captured["kwargs"]["metadata"]["request_metadata"]["run_id"] == "run-1"
    assert captured["kwargs"]["metadata"]["prompt_cache_key"] == "ses-1"
    assert captured["kwargs"]["metadata"]["has_multimodal"] is True


@pytest.mark.asyncio
async def test_kimi_agent_sdk_backend_reads_api_key_from_secret_provider(monkeypatch):
    captured = {}

    class FakeConfig:
        def __init__(self, **kwargs):
            captured["config"] = kwargs

    async def fake_prompt(prompt, **kwargs):
        captured["kwargs"] = kwargs
        yield SimpleNamespace(extract_text=lambda: "done")

    fake_sdk = SimpleNamespace(prompt=fake_prompt, Config=FakeConfig)
    monkeypatch.setitem(sys.modules, "kimi_agent_sdk", fake_sdk)
    backend = KimiAgentSdkBackend(
        base_url="https://api.moonshot.ai/v1",
        model="kimi-k2.6",
        secret_provider=_SecretProvider({"kimi.api_key": "provider-key"}),
    )

    responses = [
        response
        async for response in backend.chat([AgentMessage(role="user", content="Analyze")])
    ]

    assert responses[0].message.content == "done"
    assert captured["config"]["providers"]["kimi"]["api_key"] == "provider-key"


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
    assert '"approval_id": "appr-sdk"' in tool_call["function"]["arguments"]


@pytest.mark.asyncio
async def test_kimi_agent_sdk_backend_preserves_tool_call_id(monkeypatch):
    class FakeToolCall:
        def model_dump(self, exclude_none=True):
            return {
                "type": "tool_call",
                "id": "call-sdk",
                "name": "lookup_evidence",
                "arguments": {"query": "margin"},
            }

    async def fake_prompt(prompt, **kwargs):
        yield FakeToolCall()

    fake_sdk = SimpleNamespace(prompt=fake_prompt)
    monkeypatch.setitem(sys.modules, "kimi_agent_sdk", fake_sdk)
    backend = KimiAgentSdkBackend()

    responses = [
        response
        async for response in backend.chat([AgentMessage(role="user", content="Analyze")])
    ]

    tool_call = responses[0].message.tool_calls[0]
    assert tool_call["id"] == "call-sdk"
    assert tool_call["function"]["name"] == "lookup_evidence"
    assert '"query": "margin"' in tool_call["function"]["arguments"]


@pytest.mark.asyncio
async def test_kimi_agent_sdk_backend_preserves_reasoning_usage_and_finish_reason(monkeypatch):
    class FakeReasoningMessage:
        def model_dump(self, exclude_none=True):
            return {
                "text": "final answer",
                "reasoning_content": "thinking trace",
                "usage": {"prompt_tokens": 3, "completion_tokens": 4, "total_tokens": 7},
                "finish_reason": "stop",
            }

    async def fake_prompt(prompt, **kwargs):
        yield FakeReasoningMessage()

    fake_sdk = SimpleNamespace(prompt=fake_prompt)
    monkeypatch.setitem(sys.modules, "kimi_agent_sdk", fake_sdk)
    backend = KimiAgentSdkBackend()

    responses = [
        response
        async for response in backend.chat([AgentMessage(role="user", content="Analyze")])
    ]

    assert responses[0].message.content == "final answer"
    assert responses[0].message.reasoning_content == "thinking trace"
    assert responses[0].usage == {"prompt_tokens": 3, "completion_tokens": 4, "total_tokens": 7}
    assert responses[0].finish_reason == "stop"

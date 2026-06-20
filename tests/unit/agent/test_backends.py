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
async def test_kimi_agent_sdk_backend_stub():
    backend = KimiAgentSdkBackend()

    with pytest.raises(NotImplementedError):
        responses = backend.chat([AgentMessage(role="user", content="Analyze")])
        await responses.__anext__()

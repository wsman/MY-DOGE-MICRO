import json

import pytest

from doge.core.ports.agent_model import AgentMessage
from doge.infrastructure.agent.scripted_model import ScriptedAgentModel


async def _first_response(messages: list[AgentMessage]):
    async for response in ScriptedAgentModel().chat(messages):
        return response
    raise AssertionError("scripted model yielded no response")


@pytest.mark.asyncio
async def test_scripted_model_skips_portfolio_tool_without_explicit_portfolio():
    response = await _first_response([
        AgentMessage(role="system", content="You are OpenDoge Enterprise Research Copilot."),
        AgentMessage(role="tool", name="stock_overview", tool_call_id="call-stock-overview", content="{}"),
    ])

    assert response.message.tool_calls
    assert response.message.tool_calls[0]["function"]["name"] == "request_approval"


@pytest.mark.asyncio
async def test_scripted_model_uses_explicit_portfolio_id_from_context_marker():
    response = await _first_response([
        AgentMessage(
            role="system",
            content=(
                "You are OpenDoge Enterprise Research Copilot. "
                "Authorized run portfolio_id: portfolio-explicit.v1. "
                "Use this exact portfolio_id when portfolio tools are needed."
            ),
        ),
        AgentMessage(role="tool", name="stock_overview", tool_call_id="call-stock-overview", content="{}"),
    ])

    assert response.message.tool_calls
    call = response.message.tool_calls[0]
    assert call["function"]["name"] == "get_portfolio_exposure"
    assert json.loads(call["function"]["arguments"]) == {"portfolio_id": "portfolio-explicit.v1"}

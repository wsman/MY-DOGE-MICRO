import json
from pathlib import Path

import pytest

from doge.core.ports.agent_model import AgentMessage
from doge.infrastructure.agent.scripted_model import ScriptedAgentModel


SCENARIOS = Path("tests/fixtures/scripted_model/scenarios")


async def _first_response(model: ScriptedAgentModel, messages: list[AgentMessage]):
    async for response in model.chat(messages):
        return response
    raise AssertionError("scripted model yielded no response")


@pytest.mark.asyncio
async def test_scripted_model_loads_tool_call_scenario_from_config():
    model = ScriptedAgentModel.from_config(SCENARIOS / "market_scan.json")

    response = await _first_response(model, [AgentMessage(role="system", content="offline eval")])

    assert response.message.tool_calls
    call = response.message.tool_calls[0]
    assert call["function"]["name"] == "market_breadth"
    assert json.loads(call["function"]["arguments"]) == {"market": "us", "days": 10}


@pytest.mark.asyncio
async def test_scripted_model_loads_final_memo_path_from_config():
    model = ScriptedAgentModel.from_config(SCENARIOS / "default.json")

    response = await _first_response(model, [
        AgentMessage(role="tool", name="stock_overview", tool_call_id="call-stock-overview", content="{}"),
        AgentMessage(role="tool", name="request_approval", tool_call_id="call-approval", content="{}"),
    ])

    assert response.finish_reason == "stop"
    assert "Scenario memo generated from a fixture file" in response.message.content


@pytest.mark.asyncio
async def test_scripted_model_scenario_requires_explicit_portfolio_marker():
    model = ScriptedAgentModel.from_config(SCENARIOS / "portfolio_risk.json")

    without_marker = await _first_response(model, [
        AgentMessage(role="tool", name="stock_overview", tool_call_id="call-stock-overview", content="{}"),
    ])
    with_marker = await _first_response(model, [
        AgentMessage(
            role="system",
            content=(
                "Authorized run portfolio_id: portfolio-explicit.v1. "
                "Use this exact portfolio_id when portfolio tools are needed."
            ),
        ),
        AgentMessage(role="tool", name="stock_overview", tool_call_id="call-stock-overview", content="{}"),
    ])

    assert without_marker.message.tool_calls == []
    assert without_marker.finish_reason == "stop"
    call = with_marker.message.tool_calls[0]
    assert call["function"]["name"] == "get_portfolio_exposure"
    assert json.loads(call["function"]["arguments"]) == {"portfolio_id": "portfolio-explicit.v1"}

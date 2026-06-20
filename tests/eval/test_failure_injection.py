import json
from typing import Any, AsyncIterator

import pytest

from doge.application.agent.research_runtime import ResearchAgentRuntime
from doge.application.agent.tools import ToolRegistry, ToolResult
from doge.core.domain.agent_models import EventType, RunStatus
from doge.core.ports.agent_model import AgentMessage, AgentResponse, IAgentModel


class TimeoutThenMemoModel(IAgentModel):
    async def chat(
        self,
        messages: list[AgentMessage],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
        max_tokens: int = 16384,
        stream: bool = True,
    ) -> AsyncIterator[AgentResponse]:
        if not any(message.role == "tool" for message in messages):
            yield AgentResponse(message=AgentMessage(
                role="assistant",
                tool_calls=[{
                    "id": "call-breadth",
                    "type": "function",
                    "function": {"name": "market_breadth", "arguments": "{\"market\":\"us\",\"days\":10}"},
                }],
            ))
            return
        yield AgentResponse(
            message=AgentMessage(
                role="assistant",
                content="Market breadth data unavailable due to tool timeout. No unsupported figure is fabricated.",
            ),
            finish_reason="stop",
        )


@pytest.mark.asyncio
async def test_market_tool_timeout_degrades_without_fabrication():
    registry = ToolRegistry()
    registry.register({
        "type": "function",
        "function": {
            "name": "market_breadth",
            "description": "timeout fixture",
            "parameters": {"type": "object", "properties": {}},
        },
    }, lambda **_: ToolResult("market_breadth", data={}, ok=False, error="timeout"))
    runtime = ResearchAgentRuntime(model=TimeoutThenMemoModel(), tool_registry=registry)
    run = await runtime.create_run({"question": "Analyze market breadth."})

    run = await runtime.run_to_pause_or_completion(run.run_id)

    assert run.status == RunStatus.COMPLETED
    tool_errors = [
        event for event in run.events
        if event.event_type == EventType.TOOL_RESULT and event.payload["result"]["ok"] is False
    ]
    assert tool_errors
    assert "unavailable" in run.artifacts[0].content
    assert "fabricated" in run.artifacts[0].content


def test_eval_cases_file_has_five_smoke_cases():
    cases = json.loads(open("tests/eval/cases.json", encoding="utf-8").read())
    assert len(cases) == 5

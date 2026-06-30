import pytest

from doge.application.agent.model_response_assembler import ModelResponseAssembler
from doge.core.ports.agent_model import AgentMessage, AgentResponse


async def _streaming_chunks():
    yield AgentResponse(
        message=AgentMessage(
            role="assistant",
            content="Research ",
            reasoning_content="Need ",
            tool_calls=[{
                "index": 0,
                "id": "call-lookup",
                "type": "function",
                "function": {
                    "name": "lookup_evidence",
                    "arguments": "{\"query\":\"NV",
                },
            }],
        ),
    )
    yield AgentResponse(
        message=AgentMessage(
            role="assistant",
            content="memo",
            reasoning_content="evidence.",
            tool_calls=[{
                "index": 0,
                "function": {
                    "arguments": "DA revenue\"}",
                },
            }],
        ),
    )
    yield AgentResponse(
        message=AgentMessage(role="assistant", content="."),
        finish_reason="stop",
        usage={"prompt_tokens": 4, "completion_tokens": 3, "total_tokens": 7},
        raw={"provider": "streaming-fixture"},
    )


@pytest.mark.asyncio
async def test_model_response_assembler_merges_streaming_content_reasoning_tool_calls_and_usage():
    response = await ModelResponseAssembler().assemble(_streaming_chunks())

    assert response is not None
    assert response.message.role == "assistant"
    assert response.message.content == "Research memo."
    assert response.message.reasoning_content == "Need evidence."
    assert response.message.tool_calls == [{
        "id": "call-lookup",
        "type": "function",
        "function": {
            "name": "lookup_evidence",
            "arguments": "{\"query\":\"NVDA revenue\"}",
        },
    }]
    assert response.finish_reason == "stop"
    assert response.usage == {"prompt_tokens": 4, "completion_tokens": 3, "total_tokens": 7}
    assert response.raw == {"provider": "streaming-fixture"}

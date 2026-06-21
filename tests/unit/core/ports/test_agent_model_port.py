from abc import ABC

from doge.core.ports.agent_model import AgentContentPart, AgentMessage, AgentResponse, IAgentModel
from doge.infrastructure.llm.kimi_client import KimiAgentModel


def test_agent_model_port_is_abstract():
    assert issubclass(IAgentModel, ABC)


def test_agent_message_serializes_optional_fields():
    message = AgentMessage(
        role="assistant",
        content="memo",
        reasoning_content="reasoning",
        tool_calls=[{"id": "call-1"}],
        tool_call_id="call-1",
        name="tool_name",
    )

    assert message.to_api_dict() == {
        "role": "assistant",
        "content": "memo",
        "reasoning_content": "reasoning",
        "tool_calls": [{"id": "call-1"}],
        "tool_call_id": "call-1",
        "name": "tool_name",
    }


def test_agent_message_serializes_structured_content_parts():
    message = AgentMessage(
        role="user",
        content=[
            AgentContentPart.text_part("Describe this chart."),
            AgentContentPart.image_base64(media_type="image/png", data="abc123"),
        ],
    )

    assert message.to_api_dict()["content"] == [
        {"type": "text", "text": "Describe this chart."},
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": "abc123",
            },
        },
    ]


def test_agent_response_carries_usage_and_finish_reason():
    response = AgentResponse(
        message=AgentMessage(role="assistant", content="done"),
        finish_reason="stop",
        usage={"total_tokens": 10},
    )

    assert response.finish_reason == "stop"
    assert response.usage["total_tokens"] == 10


def test_kimi_agent_model_implements_port():
    assert issubclass(KimiAgentModel, IAgentModel)

from doge.core.ports.agent_model import AgentMessage
from doge.infrastructure.agent.kimi_sdk_adapter import KimiSdkEventAdapter


class FakeTextMessage:
    def extract_text(self):
        return "hello"


class FakeApprovalRequest:
    def __init__(self):
        self.id = "appr-1"
        self.action = "publish memo"


def test_kimi_sdk_adapter_maps_messages_to_prompt():
    adapter = KimiSdkEventAdapter()

    prompt = adapter.messages_to_prompt([
        AgentMessage(role="system", content="rules"),
        AgentMessage(role="user", content="question"),
    ])

    assert prompt == "system: rules\nuser: question"


def test_kimi_sdk_adapter_maps_text_message_to_response():
    response = KimiSdkEventAdapter().to_response(FakeTextMessage())

    assert response.message.content == "hello"


def test_kimi_sdk_adapter_maps_approval_to_existing_runtime_tool():
    response = KimiSdkEventAdapter().to_response(FakeApprovalRequest())

    assert response.message.tool_calls[0]["function"]["name"] == "request_approval"
    assert "publish memo" in response.message.tool_calls[0]["function"]["arguments"]

import pytest

from doge.application.agent.web_search_stage import WebSearchStage
from doge.core.ports.agent_model import AgentMessage, AgentResponse


class SearchModel:
    def __init__(self):
        self.calls = []

    async def chat(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        yield AgentResponse(message=AgentMessage(role="assistant", content="fresh market context"))


@pytest.mark.asyncio
async def test_web_search_stage_adds_non_thinking_context():
    model = SearchModel()
    messages = [AgentMessage(role="system", content="base")]

    result = await WebSearchStage(model).execute(messages, "query")

    assert model.calls[0][1]["thinking_enabled"] is False
    assert result[-1].role == "system"
    assert "fresh market context" in result[-1].content

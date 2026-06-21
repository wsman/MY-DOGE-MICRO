"""Optional non-thinking web-search preparation stage."""

from __future__ import annotations

from doge.application.agent.model_response_assembler import ModelResponseAssembler
from doge.core.ports.agent_model import AgentMessage, IAgentModel


class WebSearchStage:
    """Run a non-thinking search/synthesis pass before the main research call."""

    def __init__(
        self,
        model: IAgentModel,
        *,
        response_assembler: ModelResponseAssembler | None = None,
        max_tokens: int = 4096,
    ) -> None:
        self._model = model
        self._response_assembler = response_assembler or ModelResponseAssembler()
        self._max_tokens = max_tokens

    async def execute(self, messages: list[AgentMessage], query: str) -> list[AgentMessage]:
        search_messages = [
            AgentMessage(
                role="system",
                content=(
                    "Collect concise web-search context for the user query. "
                    "Return facts only; do not draft the final report."
                ),
            ),
            AgentMessage(role="user", content=query),
        ]
        response = await self._response_assembler.assemble(
            self._model.chat(
                search_messages,
                tools=None,
                tool_choice=None,
                max_tokens=self._max_tokens,
                stream=False,
                thinking_enabled=False,
            )
        )
        if response is None or not response.message.content:
            return messages
        return [
            *messages,
            AgentMessage(
                role="system",
                content=f"Web search context from non-thinking stage:\n{response.message.content}",
            ),
        ]

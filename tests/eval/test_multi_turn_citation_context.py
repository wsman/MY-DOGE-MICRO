from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest

from doge.application.agent.tools import ToolRegistry
from doge.bootstrap.runtime import RuntimeContainer
from doge.core.domain.agent_models import RunStatus
from doge.core.ports.agent_model import AgentMessage, AgentResponse, IAgentModel
from doge.infrastructure.database.agent_repositories import SQLiteSessionRepository


class MultiTurnCitationModel(IAgentModel):
    """Deterministic model that requires prior artifact citations on turn two."""

    def __init__(self) -> None:
        self.second_turn_metrics: dict[str, bool] = {}

    async def chat(
        self,
        messages: list[AgentMessage],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
        max_tokens: int = 16384,
        max_completion_tokens: int | None = None,
        stream: bool = True,
        model: str | None = None,
        thinking_enabled: bool | None = None,
        response_format: dict[str, Any] | None = None,
        prompt_cache_key: str | None = None,
        safety_identifier: str | None = None,
        timeout: float | None = None,
        request_metadata: dict[str, Any] | None = None,
        extra_body: dict[str, Any] | None = None,
    ) -> AsyncIterator[AgentResponse]:
        del tools, tool_choice, max_tokens, max_completion_tokens, stream, model
        del thinking_enabled, response_format, prompt_cache_key, safety_identifier, timeout
        del request_metadata, extra_body
        current_question = _last_user_text(messages)
        if "follow up" in current_question.lower():
            context_text = "\n".join(str(message.content) for message in messages)
            self.second_turn_metrics = {
                "prior_user_turn_retained": "What drove Q2 revenue?" in context_text,
                "prior_artifact_retained": "First memo: revenue grew 12%" in context_text,
                "prior_citation_retained": "[^evd-prior]" in context_text,
                "current_turn_not_duplicated": context_text.count("Follow up on the same revenue claim") == 1,
            }
            yield AgentResponse(
                message=AgentMessage(
                    role="assistant",
                    content="Second memo reuses the prior cited revenue claim [^evd-prior].",
                ),
                finish_reason="stop",
                usage={"prompt_tokens": 12, "completion_tokens": 7, "total_tokens": 19},
            )
            return

        yield AgentResponse(
            message=AgentMessage(
                role="assistant",
                content="First memo: revenue grew 12% on product demand [^evd-prior].",
            ),
            finish_reason="stop",
            usage={"prompt_tokens": 8, "completion_tokens": 9, "total_tokens": 17},
        )


def _last_user_text(messages: list[AgentMessage]) -> str:
    for message in reversed(messages):
        if message.role == "user" and isinstance(message.content, str):
            return message.content
    return ""


@pytest.mark.asyncio
async def test_level_1_multi_turn_citation_context_benchmark(tmp_path):
    """Two embedded CLI-session turns retain prior user turn and artifact citations."""
    db = tmp_path / "agent_state.db"
    container = RuntimeContainer(db_path=db)
    session = container.build_create_session_use_case().execute("Multi-turn citation")
    model = MultiTurnCitationModel()
    execute = container.build_execute_run_use_case(
        model=model,
        tool_registry=ToolRegistry(),
    )

    first = await execute.execute(
        "What drove Q2 revenue?",
        session_id=session.session_id,
        model_policy={"max_tool_rounds": 1, "stream": True},
    )
    second = await execute.execute(
        "Follow up on the same revenue claim with citation continuity.",
        session_id=session.session_id,
        model_policy={"max_tool_rounds": 1, "stream": True},
    )
    persisted_session = SQLiteSessionRepository(db).get(session.session_id)

    assert first.status == RunStatus.COMPLETED
    assert second.status == RunStatus.COMPLETED
    assert persisted_session is not None
    assert [turn.run_id for turn in persisted_session.turns] == [first.run_id, second.run_id]
    assert all(model.second_turn_metrics.values()), model.second_turn_metrics
    assert second.artifacts
    assert "[^evd-prior]" in second.artifacts[-1].content

"""Use cases for executing persisted agent runs."""

from __future__ import annotations

from typing import Any

from doge.application.use_cases.session_use_cases import AppendTurn
from doge.core.domain.agent_models import AgentRun
from doge.core.domain.model_policy import ModelPolicy
from doge.core.ports.agent_repository import ISessionRepository
from doge.core.ports.agent_runtime import IResearchAgentRuntime
from doge.shared.scope import TenantScope


class ExecuteRun:
    def __init__(self, runtime: IResearchAgentRuntime, sessions: ISessionRepository | None = None) -> None:
        self._runtime = runtime
        self._append_turn = AppendTurn(sessions) if sessions is not None else None

    async def execute(
        self,
        question: str,
        *,
        session_id: str | None = None,
        market: str = "us",
        language: str = "en",
        document_ids: list[str] | None = None,
        portfolio_id: str | None = "portfolio-demo",
        model_policy: dict[str, Any] | ModelPolicy | None = None,
    ) -> AgentRun:
        run = await self._runtime.create_run({
            "workflow": "investment_research",
            "question": question,
            "session_id": session_id,
            "market": market,
            "language": language,
            "document_ids": document_ids or [],
            "portfolio_id": portfolio_id,
            "model_policy": ModelPolicy.from_dict(model_policy or {"max_tool_rounds": 8}),
        })
        if session_id and self._append_turn is not None:
            self._append_turn.execute(session_id, question, run.run_id)
        return await self._runtime.run_to_pause_or_completion(run.run_id)


class ResumeRun:
    def __init__(self, runtime: IResearchAgentRuntime) -> None:
        self._runtime = runtime

    def execute(self, run_id: str) -> AgentRun | None:
        return self._runtime.get_run(TenantScope.local(), run_id)

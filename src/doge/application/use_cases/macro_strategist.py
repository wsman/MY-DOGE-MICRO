"""Runtime-backed macro strategist use case."""

from __future__ import annotations

from doge.core.domain.agent_models import AgentRun
from doge.core.domain.model_policy import ModelPolicy
from doge.core.ports.agent_runtime import IResearchAgentRuntime
from doge.shared.scope import TenantScope


RESEARCH_PATH = "runtime_research_copilot"


class MacroStrategistAgentUseCase:
    """Create a governed RuntimeKernel Research Copilot run for macro strategy analysis."""

    def __init__(self, runtime: IResearchAgentRuntime) -> None:
        self._runtime = runtime

    async def execute(
        self,
        *,
        market: str = "us",
        question: str | None = None,
        session_id: str | None = None,
        document_ids: list[str] | None = None,
        portfolio_id: str | None = None,
        model_policy: dict | ModelPolicy | None = None,
    ) -> AgentRun:
        scope = TenantScope.local()
        run = await self._runtime.create_run(
            scope,
            {
                "workflow": "macro_research",
                "question": question or _default_question(market),
                "session_id": session_id,
                "market": market,
                "document_ids": document_ids or [],
                "portfolio_id": portfolio_id,
                "model_policy": ModelPolicy.from_dict(model_policy or {
                    "execution_profile": "financial_research",
                    "max_tool_rounds": 8,
                }),
            },
        )
        return await self._runtime.run_to_pause_or_completion(scope, run.run_id)


def _default_question(market: str) -> str:
    return (
        f"Prepare a source-grounded macro strategy memo for the {market.upper()} market. "
        "Use deterministic market and portfolio tools for material numbers, cite evidence, "
        "and mark unverifiable claims as insufficient_evidence."
    )

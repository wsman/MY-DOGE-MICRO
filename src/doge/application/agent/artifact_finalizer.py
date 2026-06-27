"""Artifact finalization service for runtime runs."""

from __future__ import annotations

from doge.core.domain.agent_models import AgentArtifact, AgentEvent, AgentRun
from doge.core.domain.run_execution_context import RunExecutionContext
from doge.core.ports.runtime_services import IArtifactEvaluationService


class ArtifactFinalizer:
    """Build and evaluate the final artifact for a completed run step."""

    def __init__(self, *, evaluation_service: IArtifactEvaluationService) -> None:
        self._evaluation = evaluation_service

    def build_artifact(
        self,
        run: AgentRun,
        response_content: str,
        events: list[AgentEvent],
        *,
        usage: dict | None = None,
    ) -> AgentArtifact:
        """Create the investment memo artifact and attach evaluation metrics."""
        content = self._evaluation.artifact_content(response_content)
        return run.add_artifact(
            kind="investment_memo",
            title="Investment Committee Memo",
            content=content,
            data={**self._evaluation.metrics(content, events), "usage": usage or {}},
        )

    @staticmethod
    def execution_context(run: AgentRun) -> RunExecutionContext:
        return RunExecutionContext.from_run(run)

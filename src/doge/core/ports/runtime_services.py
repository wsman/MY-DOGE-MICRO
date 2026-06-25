"""Runtime execution service ports shared by the agent kernel."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from doge.core.domain.agent_models import AgentEvent, AgentRun
from doge.core.domain.enterprise_context import EnterpriseContext
from doge.core.domain.model_policy import ModelPolicy
from doge.core.domain.run_execution_context import RunExecutionContext
from doge.core.ports.model_router import RoutingDecision


@dataclass(frozen=True)
class ModelExecutionResult:
    response: Any
    routing: RoutingDecision | None
    routing_payload: dict[str, Any]
    budget_exceeded: bool = False


@dataclass(frozen=True)
class ToolResult:
    name: str
    data: dict[str, Any]
    ok: bool = True
    error: str | None = None
    safe_error: dict[str, str] | None = None

    def to_json(self) -> str:
        import json

        return json.dumps({
            "ok": self.ok,
            "name": self.name,
            "data": self.data,
            "error": self.error,
            "safe_error": self.safe_error,
        }, ensure_ascii=False)


class IModelExecutionService(Protocol):
    async def execute(
        self,
        *,
        run: AgentRun,
        policy: ModelPolicy,
        messages: list[Any],
        tool_schemas_for: Callable[[RoutingDecision | None], list[dict[str, Any]]],
        enterprise_context: EnterpriseContext | None = None,
        execution_context: RunExecutionContext | None = None,
    ) -> ModelExecutionResult:
        ...


class IToolExecutionService(Protocol):
    def schemas_for(
        self,
        routing: RoutingDecision | None,
        context: EnterpriseContext | None = None,
    ) -> list[dict[str, Any]]:
        ...

    async def execute(
        self,
        *,
        context: EnterpriseContext | None,
        tool_name: str,
        arguments: str,
        run_id: str,
        timeout_seconds: float | None,
        request_id: str | None,
    ) -> ToolResult:
        ...

    def audit(
        self,
        context: EnterpriseContext | None,
        event_type: str,
        resource_type: str,
        resource_id: str,
        metadata: dict[str, Any] | None = None,
        *,
        request_id: str | None = None,
    ) -> None:
        ...


class IArtifactEvaluationService(Protocol):
    def artifact_content(self, content: str | None) -> str:
        ...

    def metrics(self, artifact_text: str, events: list[AgentEvent]) -> dict[str, Any]:
        ...

"""Port for per-run model routing decisions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from doge.core.domain.agent_models import AgentRun
from doge.core.domain.model_policy import ModelPolicy
from doge.core.domain.run_execution_context import RunExecutionContext


@dataclass(frozen=True)
class RoutingDecision:
    backend: str
    model: str
    thinking_enabled: bool
    model_family: str | None = None
    max_completion_tokens: int | None = None
    response_format: dict[str, Any] | None = None
    prompt_cache_key: str | None = None
    safety_identifier: str | None = None
    run_budget_usd: float | None = None
    preserve_reasoning_content: bool = False
    files_purpose: str | None = None
    tool_names: list[str] | None = None
    extra_body: dict[str, Any] = field(default_factory=dict)


class IModelRouter(Protocol):
    def route(
        self,
        run: AgentRun,
        policy: ModelPolicy,
        *,
        execution_context: RunExecutionContext | None = None,
    ) -> RoutingDecision:
        ...

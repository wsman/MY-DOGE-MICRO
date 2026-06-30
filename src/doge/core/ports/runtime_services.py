"""Runtime execution service ports shared by the agent kernel."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import Any, Protocol

from doge.core.domain.agent_models import AgentArtifact, AgentEvent, AgentRun
from doge.core.domain.enterprise_context import EnterpriseContext
from doge.core.domain.evidence_chunk_models import EvidenceChunk
from doge.core.domain.model_policy import ModelPolicy
from doge.core.domain.run_execution_context import RunExecutionContext
from doge.core.ports.model_router import RoutingDecision
from doge.shared.scope import TenantScope


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
    evidence_refs: list[EvidenceChunk] | None = None

    def to_json(self) -> str:
        import json

        payload = {
            "ok": self.ok,
            "name": self.name,
            "data": self.data,
            "error": self.error,
            "safe_error": self.safe_error,
        }
        if self.evidence_refs is not None:
            payload["evidence_refs"] = [ref.to_dict() for ref in self.evidence_refs]
        return json.dumps(payload, ensure_ascii=False)


class IModelResponseAssembler(Protocol):
    async def assemble(self, chunks: AsyncIterator[Any]) -> Any | None:
        ...


class IWebSearchStage(Protocol):
    async def execute(self, messages: list[Any], query: str) -> list[Any]:
        ...


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


class ITransitionRecorder(Protocol):
    async def record(
        self,
        run: AgentRun,
        *,
        status: Any = None,
        events: list[tuple[Any, dict[str, Any]]] | None = None,
        artifacts: list[Any] | None = None,
        approvals: list[Any] | None = None,
        save_run: bool = False,
    ) -> list[AgentEvent]:
        ...


class IRunStepper(Protocol):
    async def step(self, scope: TenantScope, run_id: str) -> AgentRun:
        ...


class IApprovalCoordinator(Protocol):
    async def resolve(
        self,
        scope: TenantScope,
        run_id: str,
        approval_id: str,
        approved: bool,
    ) -> AgentRun:
        ...


class IArtifactFinalizer(Protocol):
    def build_artifact(
        self,
        run: AgentRun,
        response_content: str,
        events: list[AgentEvent],
        *,
        usage: dict[str, Any] | None = None,
        citation_data: dict[str, Any] | None = None,
    ) -> AgentArtifact:
        ...


class IRunLifecycleService(Protocol):
    async def create_run(self, scope: TenantScope, request: dict[str, Any]) -> AgentRun:
        ...

    async def run_to_pause_or_completion(self, scope: TenantScope, run_id: str) -> AgentRun:
        ...

    async def queue_run(
        self,
        scope: TenantScope,
        run_id: str,
        reason: str = "queued",
    ) -> AgentRun:
        ...

    async def resume_run(self, scope: TenantScope, run_id: str) -> AgentRun:
        ...

    async def cancel_run(
        self,
        scope: TenantScope,
        run_id: str,
    ) -> AgentRun:
        ...

    async def finalize_cancelled(
        self,
        scope: TenantScope,
        run_id: str,
    ) -> AgentRun:
        ...

    async def record_failure(
        self,
        scope: TenantScope,
        run_id: str,
        message: str,
    ) -> AgentRun:
        ...

    def get_run(
        self,
        scope: TenantScope,
        run_id: str,
    ) -> AgentRun | None:
        ...

    def list_events(
        self,
        scope: TenantScope,
        run_id: str,
    ) -> list[AgentEvent]:
        ...

    def list_runs(
        self,
        scope: TenantScope,
        session_id: str | None = None,
        limit: int = 20,
    ) -> list[AgentRun]:
        ...

    def list_artifacts(
        self,
        scope: TenantScope,
        run_id: str,
    ) -> list[Any]:
        ...

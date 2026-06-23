"""Persisted research-agent runtime kernel."""

from __future__ import annotations

from typing import Any

from doge.application.agent.context_builder import ContextBuilder
from doge.application.agent.model_response_assembler import ModelResponseAssembler
from doge.application.agent.state_machine import ensure_transition
from doge.application.agent.tools import ToolRegistry
from doge.application.agent.web_search_stage import WebSearchStage
from doge.core.domain.agent_models import (
    AgentEvent,
    AgentRun,
    EventType,
    RunStatus,
    utc_now,
)
from doge.core.domain.enterprise_context import EnterpriseContext
from doge.core.domain.model_policy import ModelPolicy
from doge.core.ports.agent_model import IAgentModel
from doge.core.ports.agent_backend import IAgentBackend
from doge.core.ports.agent_repository import (
    IApprovalRepository,
    IArtifactRepository,
    IEventRepository,
    IRunRepository,
)
from doge.core.ports.event_publisher import IEventPublisher
from doge.core.ports.enterprise_governance import IEnterpriseGovernanceRepository
from doge.core.ports.model_router import IModelRouter
from doge.platform.runtime.services import (
    ArtifactEvaluationService,
    ModelExecutionService,
    ToolExecutionService,
)


class _NoopEventPublisher:
    async def publish(self, event: AgentEvent) -> None:
        return None


class RuntimeKernel:
    """Business logic for agent runs without owning storage policy."""

    def __init__(
        self,
        *,
        model: IAgentModel,
        tool_registry: ToolRegistry,
        run_repository: IRunRepository,
        event_repository: IEventRepository,
        artifact_repository: IArtifactRepository,
        approval_repository: IApprovalRepository,
        event_publisher: IEventPublisher | None = None,
        context_builder: ContextBuilder | None = None,
        response_assembler: ModelResponseAssembler | None = None,
        model_router: IModelRouter | None = None,
        web_search_stage: WebSearchStage | None = None,
        agent_backends: dict[str, IAgentBackend] | None = None,
        governance_repository: IEnterpriseGovernanceRepository | None = None,
        model_execution_service: ModelExecutionService | None = None,
        tool_execution_service: ToolExecutionService | None = None,
        artifact_evaluation_service: ArtifactEvaluationService | None = None,
    ) -> None:
        self._model = model
        self._tools = tool_registry
        self._runs = run_repository
        self._events = event_repository
        self._artifacts = artifact_repository
        self._approvals = approval_repository
        self._publisher = event_publisher or _NoopEventPublisher()
        self._context_builder = context_builder or ContextBuilder()
        self._response_assembler = response_assembler or ModelResponseAssembler()
        self._model_router = model_router
        self._web_search_stage = web_search_stage
        self._agent_backends = agent_backends or {}
        self._governance = governance_repository
        self._model_execution = model_execution_service or ModelExecutionService(
            model=model,
            response_assembler=self._response_assembler,
            model_router=model_router,
            web_search_stage=web_search_stage,
            agent_backends=self._agent_backends,
        )
        self._tool_execution = tool_execution_service or ToolExecutionService(
            tool_registry=tool_registry,
            governance_repository=governance_repository,
        )
        self._artifact_evaluation = artifact_evaluation_service or ArtifactEvaluationService()

    async def create_run(self, request: dict[str, Any]) -> AgentRun:
        run = AgentRun.create(
            workflow=request.get("workflow", "investment_research"),
            question=request.get("question", ""),
            session_id=request.get("session_id"),
            market=request.get("market", "us"),
            language=request.get("language", "en"),
            document_ids=list(request.get("document_ids", [])),
            portfolio_id=request.get("portfolio_id"),
            model_policy=ModelPolicy.from_dict(request.get("model_policy")),
        )
        self._runs.save(run)
        payload = {"question": run.question, "workflow": run.workflow}
        template = request.get("template")
        if isinstance(template, dict):
            payload["template"] = template
        await self._add_event(run, EventType.RUN_CREATED, payload)
        return self._hydrate(run.run_id)

    async def run_to_pause_or_completion(self, run_id: str) -> AgentRun:
        run = self._require_run(run_id)
        policy = ModelPolicy.from_dict(run.model_policy)
        max_rounds = policy.max_tool_rounds
        for _ in range(max_rounds):
            run = await self.step(run_id)
            if run.status in {
                RunStatus.AWAITING_APPROVAL,
                RunStatus.CANCELLED,
                RunStatus.COMPLETED,
                RunStatus.FAILED,
            }:
                return run
        await self._fail(run, "max tool rounds exceeded")
        return self._hydrate(run_id)

    async def queue_run(self, run_id: str, reason: str = "queued") -> AgentRun:
        run = self._require_run(run_id)
        if run.status == RunStatus.QUEUED:
            return run
        if run.status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}:
            return run
        self._set_status(run, RunStatus.QUEUED)
        await self._add_event(run, EventType.RUN_QUEUED, {"reason": reason})
        return self._hydrate(run_id)

    async def step(self, run_id: str) -> AgentRun:
        run = self._require_run(run_id)
        if run.status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}:
            return run
        if run.status == RunStatus.CANCELLING:
            return await self._mark_cancelled(run)

        self._set_status(run, RunStatus.RUNNING)
        policy = ModelPolicy.from_dict(run.model_policy)
        tenant_id = _tenant_id_for_policy(policy)
        enterprise_context = _enterprise_context_from_policy(policy)
        events = self._events.list_for_run(run.run_id, tenant_id=tenant_id)
        messages = self._context_builder.build(run, events, enterprise_context=enterprise_context)
        model_result = await self._model_execution.execute(
            run=run,
            policy=policy,
            messages=messages,
            tool_schemas_for=lambda routing: self._tool_execution.schemas_for(routing, enterprise_context),
        )
        self._tool_execution.audit(
            enterprise_context,
            "model_route",
            "run",
            run.run_id,
            {
                "backend": getattr(model_result.routing, "backend", None),
                "model": getattr(model_result.routing, "model", None),
                "execution_profile": policy.execution_profile,
            },
            request_id=_request_id(policy),
        )
        response = model_result.response
        run = self._require_run(run_id)
        if run.status == RunStatus.CANCELLING:
            return await self._mark_cancelled(run)
        if response is None:
            await self._fail(run, "model unavailable")
            return self._hydrate(run.run_id)

        await self._add_event(run, EventType.MODEL_RESPONSE, {
            "message": response.message.to_api_dict(),
            "finish_reason": response.finish_reason,
            "usage": response.usage or {},
            "routing": model_result.routing_payload,
        })
        if model_result.budget_exceeded:
            await self._fail(run, "run budget exceeded")
            return self._hydrate(run.run_id)

        if response.message.tool_calls:
            for call in response.message.tool_calls:
                run = self._require_run(run_id)
                if run.status == RunStatus.CANCELLING:
                    return await self._mark_cancelled(run)
                function = call.get("function", {})
                name = function.get("name", "")
                arguments = function.get("arguments", "{}")
                await self._add_event(run, EventType.TOOL_CALL, {"tool_call": call})
                timeout = policy.tool_timeout_seconds
                result = await self._tool_execution.execute(
                    context=enterprise_context,
                    tool_name=name,
                    arguments=arguments,
                    run_id=run.run_id,
                    timeout_seconds=float(timeout) if timeout else None,
                    request_id=_request_id(policy),
                )
                run = self._require_run(run_id)
                if run.status == RunStatus.CANCELLING:
                    return await self._mark_cancelled(run)
                result_payload = {
                    "ok": result.ok,
                    "name": result.name,
                    "data": result.data,
                    "error": result.error,
                }
                await self._add_event(run, EventType.TOOL_RESULT, {
                    "tool_call_id": call.get("id"),
                    "name": name,
                    "result": result_payload,
                })
                if result.data.get("approval_required"):
                    approval = run.add_approval(
                        action=result.data.get("action", name),
                        risk_level=result.data.get("risk_level", "high"),
                    )
                    self._approvals.save(approval, tenant_id=tenant_id)
                    self._set_status(run, RunStatus.AWAITING_APPROVAL)
                    await self._add_event(run, EventType.APPROVAL_REQUESTED, {
                        "approval_id": approval.approval_id,
                        "action": approval.action,
                        "risk_level": approval.risk_level,
                    })
                    return self._hydrate(run.run_id)
            self._set_status(run, RunStatus.RUNNING)
            return self._hydrate(run.run_id)

        content = self._artifact_evaluation.artifact_content(response.message.content)
        events = self._events.list_for_run(run.run_id, tenant_id=tenant_id)
        artifact = run.add_artifact(
            kind="investment_memo",
            title="Investment Committee Memo",
            content=content,
            data={**self._artifact_evaluation.metrics(content, events), "usage": response.usage or {}},
        )
        self._artifacts.save(artifact, tenant_id=tenant_id)
        self._set_status(run, RunStatus.COMPLETED)
        await self._add_event(run, EventType.ARTIFACT_CREATED, {
            "artifact_id": artifact.artifact_id,
            "kind": artifact.kind,
            "title": artifact.title,
        })
        return self._hydrate(run.run_id)

    async def resolve_approval(self, run_id: str, approval_id: str, approved: bool) -> AgentRun:
        run = self._require_run(run_id)
        tenant_id = _tenant_id_for_policy(run.model_policy)
        approval = self._approvals.get(approval_id, tenant_id=tenant_id)
        if approval is None or approval.run_id != run_id:
            raise KeyError(f"approval not found: {approval_id}")
        approval.status = "approved" if approved else "denied"
        approval.resolved_at = utc_now()
        self._approvals.save(approval, tenant_id=tenant_id)
        await self._add_event(run, EventType.APPROVAL_RESOLVED, {
            "approval_id": approval_id,
            "approved": approved,
        })
        if not approved:
            self._set_status(run, RunStatus.FAILED)
            return self._hydrate(run_id)
        self._set_status(run, RunStatus.QUEUED)
        await self._add_event(run, EventType.RUN_QUEUED, {"reason": "approval_resolved"})
        return self._hydrate(run_id)

    async def cancel_run(self, run_id: str) -> AgentRun:
        run = self._require_run(run_id)
        if run.status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}:
            return run
        if run.status != RunStatus.CANCELLING:
            self._set_status(run, RunStatus.CANCELLING)
            run = self._require_run(run_id)
        run.cancel_requested_at = utc_now()
        self._runs.save(run)
        return self._hydrate(run_id)

    async def finalize_cancelled(self, run_id: str) -> AgentRun:
        run = self._require_run(run_id)
        if run.status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}:
            return run
        return await self._mark_cancelled(run)

    def get_run(self, run_id: str) -> AgentRun | None:
        return self._runs.get(run_id)

    def list_events(self, run_id: str) -> list[AgentEvent]:
        return self._events.list_for_run(run_id)

    def list_runs(self, session_id: str | None = None, limit: int = 20) -> list[AgentRun]:
        if session_id:
            return self._runs.list_by_session(session_id)
        return self._runs.list_recent(limit)

    def list_artifacts(self, run_id: str):
        return self._artifacts.list_for_run(run_id)

    async def _mark_cancelled(self, run: AgentRun) -> AgentRun:
        self._set_status(run, RunStatus.CANCELLED)
        await self._add_event(run, EventType.RUN_CANCELLED, {"cancelled": True})
        return self._hydrate(run.run_id)

    async def _fail(self, run: AgentRun, message: str) -> None:
        self._set_status(run, RunStatus.FAILED)
        await self._add_event(run, EventType.ERROR, {"message": message})

    def _set_status(self, run: AgentRun, status: RunStatus) -> None:
        ensure_transition(run.status, status)
        run.status = status
        run.updated_at = utc_now()
        self._runs.save(run)

    async def _add_event(self, run: AgentRun, event_type: EventType, payload: dict[str, Any]) -> AgentEvent:
        event = run.add_event(event_type, payload)
        event = self._events.append(event, tenant_id=_tenant_id_for_policy(run.model_policy))
        await self._publisher.publish(event)
        return event

    def _require_run(self, run_id: str) -> AgentRun:
        run = self._runs.get(run_id)
        if run is None:
            raise KeyError(f"run not found: {run_id}")
        return run

    def _hydrate(self, run_id: str) -> AgentRun:
        return self._require_run(run_id)


def _enterprise_context_from_policy(policy: ModelPolicy) -> EnterpriseContext:
    extra = policy.extra
    return EnterpriseContext(
        tenant_id=policy.tenant_id or _string_value(extra.get("tenant_id"), "local"),
        user_hash=policy.user_hash or _string_value(extra.get("user_hash"), "local-user"),
        role=_string_value(extra.get("role"), "analyst"),
        document_acl=frozenset(_string_set(extra.get("document_acl"))),
        tool_entitlement=frozenset(_string_set(extra.get("tool_entitlement"))),
        portfolio_permission=frozenset(_string_set(extra.get("portfolio_permission"))),
        data_classification=_string_value(extra.get("data_classification"), "internal"),
        approval_authority=frozenset(_string_set(extra.get("approval_authority"))),
        project_id=_string_value(extra.get("project_id"), "doge-dev"),
    )


def _request_id(policy: ModelPolicy) -> str | None:
    value = policy.extra.get("request_id")
    if value is None or value == "":
        return None
    return str(value)


def _tenant_id_for_policy(policy: ModelPolicy | dict[str, Any]) -> str | None:
    normalized = ModelPolicy.from_dict(policy)
    tenant_id = normalized.tenant_id or normalized.extra.get("tenant_id")
    return str(tenant_id) if tenant_id else None


def _string_set(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        return {item.strip() for item in value.split(",") if item.strip()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return {str(item) for item in value if item is not None and str(item) != ""}
    return {str(value)}


def _string_value(value: Any, default: str) -> str:
    if value is None or value == "":
        return default
    return str(value)

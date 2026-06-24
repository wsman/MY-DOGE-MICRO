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
from doge.core.domain.enterprise_context import IdentitySnapshot
from doge.core.domain.model_policy import ModelPolicy
from doge.core.domain.run_execution_context import RunExecutionContext
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
from doge.core.ports.runtime_transaction import IRuntimeTransaction, IRuntimeTransactionFactory
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
        runtime_transaction_factory: IRuntimeTransactionFactory | None = None,
    ) -> None:
        self._model = model
        self._tools = tool_registry
        self._runs = run_repository
        self._events = event_repository
        self._artifacts = artifact_repository
        self._approvals = approval_repository
        self._publisher = event_publisher or _NoopEventPublisher()
        self._transactions = runtime_transaction_factory or _RepositoryRuntimeTransactionFactory(
            run_repository=run_repository,
            event_repository=event_repository,
            artifact_repository=artifact_repository,
            approval_repository=approval_repository,
        )
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
        model_policy_payload = request.get("model_policy")
        run = AgentRun.create(
            workflow=request.get("workflow", "investment_research"),
            question=request.get("question", ""),
            session_id=request.get("session_id"),
            market=request.get("market", "us"),
            language=request.get("language", "en"),
            document_ids=list(request.get("document_ids", [])),
            portfolio_id=request.get("portfolio_id"),
            model_policy=ModelPolicy.from_dict(model_policy_payload),
            identity_snapshot=_identity_snapshot_from_request(request, model_policy_payload),
        )
        payload = {"question": run.question, "workflow": run.workflow}
        template = request.get("template")
        if isinstance(template, dict):
            payload["template"] = template
        await self._record_transition(run, events=[(EventType.RUN_CREATED, payload)], save_run=True)
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
        await self._record_transition(
            run,
            status=RunStatus.QUEUED,
            events=[(EventType.RUN_QUEUED, {"reason": reason})],
        )
        return self._hydrate(run_id)

    async def step(self, run_id: str) -> AgentRun:
        run = self._require_run(run_id)
        if run.status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}:
            return run
        if run.status == RunStatus.CANCELLING:
            return await self._mark_cancelled(run)

        await self._record_transition(run, status=RunStatus.RUNNING)
        run = self._require_run(run_id)
        execution_context = RunExecutionContext.from_run(run)
        policy = execution_context.model_policy
        tenant_id = _tenant_id_for_run(run)
        enterprise_context = execution_context.enterprise_context
        events = self._events.list_for_run(run.run_id, tenant_id=tenant_id)
        messages = self._context_builder.build(
            run,
            events,
            enterprise_context=enterprise_context,
            execution_context=execution_context,
        )
        model_result = await self._model_execution.execute(
            run=run,
            policy=policy,
            messages=messages,
            tool_schemas_for=lambda routing: self._tool_execution.schemas_for(routing, enterprise_context),
            enterprise_context=enterprise_context,
            execution_context=execution_context,
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
            request_id=execution_context.request_id,
        )
        response = model_result.response
        run = self._require_run(run_id)
        if run.status == RunStatus.CANCELLING:
            return await self._mark_cancelled(run)
        if response is None:
            await self._fail(run, "model unavailable")
            return self._hydrate(run.run_id)

        await self._record_transition(
            run,
            events=[(EventType.MODEL_RESPONSE, {
                "message": response.message.to_api_dict(),
                "finish_reason": response.finish_reason,
                "usage": response.usage or {},
                "routing": model_result.routing_payload,
            })],
        )
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
                await self._record_transition(run, events=[(EventType.TOOL_CALL, {"tool_call": call})])
                timeout = policy.tool_timeout_seconds
                result = await self._tool_execution.execute(
                    context=enterprise_context,
                    tool_name=name,
                    arguments=arguments,
                    run_id=run.run_id,
                    timeout_seconds=float(timeout) if timeout else None,
                    request_id=execution_context.request_id,
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
                await self._record_transition(
                    run,
                    events=[(EventType.TOOL_RESULT, {
                        "tool_call_id": call.get("id"),
                        "name": name,
                        "result": result_payload,
                    })],
                )
                if result.data.get("approval_required"):
                    approval = run.add_approval(
                        action=result.data.get("action", name),
                        risk_level=result.data.get("risk_level", "high"),
                    )
                    await self._record_transition(
                        run,
                        status=RunStatus.AWAITING_APPROVAL,
                        approvals=[approval],
                        events=[(EventType.APPROVAL_REQUESTED, {
                            "approval_id": approval.approval_id,
                            "action": approval.action,
                            "risk_level": approval.risk_level,
                        })],
                    )
                    return self._hydrate(run.run_id)
            await self._record_transition(run, status=RunStatus.RUNNING)
            return self._hydrate(run.run_id)

        content = self._artifact_evaluation.artifact_content(response.message.content)
        events = self._events.list_for_run(run.run_id, tenant_id=tenant_id)
        artifact = run.add_artifact(
            kind="investment_memo",
            title="Investment Committee Memo",
            content=content,
            data={**self._artifact_evaluation.metrics(content, events), "usage": response.usage or {}},
        )
        await self._record_transition(
            run,
            status=RunStatus.COMPLETED,
            artifacts=[artifact],
            events=[(EventType.ARTIFACT_CREATED, {
                "artifact_id": artifact.artifact_id,
                "kind": artifact.kind,
                "title": artifact.title,
            })],
        )
        return self._hydrate(run.run_id)

    async def resolve_approval(self, run_id: str, approval_id: str, approved: bool) -> AgentRun:
        run = self._require_run(run_id)
        tenant_id = _tenant_id_for_run(run)
        approval = self._approvals.get(approval_id, tenant_id=tenant_id)
        if approval is None or approval.run_id != run_id:
            raise KeyError(f"approval not found: {approval_id}")
        approval.status = "approved" if approved else "denied"
        approval.resolved_at = utc_now()
        if not approved:
            await self._record_transition(
                run,
                status=RunStatus.FAILED,
                approvals=[approval],
                events=[(EventType.APPROVAL_RESOLVED, {
                    "approval_id": approval_id,
                    "approved": approved,
                })],
            )
            return self._hydrate(run_id)
        await self._record_transition(
            run,
            status=RunStatus.QUEUED,
            approvals=[approval],
            events=[
                (EventType.APPROVAL_RESOLVED, {
                    "approval_id": approval_id,
                    "approved": approved,
                }),
                (EventType.RUN_QUEUED, {"reason": "approval_resolved"}),
            ],
        )
        return self._hydrate(run_id)

    async def cancel_run(self, run_id: str) -> AgentRun:
        run = self._require_run(run_id)
        if run.status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}:
            return run
        run.cancel_requested_at = utc_now()
        if run.status != RunStatus.CANCELLING:
            await self._record_transition(run, status=RunStatus.CANCELLING)
            run = self._require_run(run_id)
        else:
            await self._record_transition(run, save_run=True)
        return self._hydrate(run_id)

    async def finalize_cancelled(self, run_id: str) -> AgentRun:
        run = self._require_run(run_id)
        if run.status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}:
            return run
        return await self._mark_cancelled(run)

    async def record_failure(self, run_id: str, message: str) -> AgentRun:
        run = self._require_run(run_id)
        if run.status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}:
            return run
        await self._fail(run, message)
        return self._hydrate(run_id)

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
        await self._record_transition(
            run,
            status=RunStatus.CANCELLED,
            events=[(EventType.RUN_CANCELLED, {"cancelled": True})],
        )
        return self._hydrate(run.run_id)

    async def _fail(self, run: AgentRun, message: str) -> None:
        await self._record_transition(
            run,
            status=RunStatus.FAILED,
            events=[(EventType.ERROR, {"message": message})],
        )

    async def _record_transition(
        self,
        run: AgentRun,
        *,
        status: RunStatus | None = None,
        events: list[tuple[EventType, dict[str, Any]]] | None = None,
        artifacts: list[Any] | None = None,
        approvals: list[Any] | None = None,
        save_run: bool = False,
    ) -> list[AgentEvent]:
        if status is not None:
            ensure_transition(run.status, status)
            run.status = status
            run.updated_at = utc_now()
            save_run = True
        staged_events = [run.add_event(event_type, payload) for event_type, payload in (events or [])]
        tx = self._transactions.begin()
        persisted_events: list[AgentEvent] = []
        try:
            if save_run:
                tx.save_run(run)
            for event in staged_events:
                persisted_event = tx.append_event(event)
                tx.stage_outbox(persisted_event)
                persisted_events.append(persisted_event)
            for approval in approvals or []:
                tx.save_approval(approval)
            for artifact in artifacts or []:
                tx.save_artifact(artifact)
            tx.commit()
        except Exception:
            tx.rollback()
            raise
        for event in persisted_events:
            await self._publisher.publish(event)
        return persisted_events

    def _require_run(self, run_id: str) -> AgentRun:
        run = self._runs.get(run_id)
        if run is None:
            raise KeyError(f"run not found: {run_id}")
        return run

    def _hydrate(self, run_id: str) -> AgentRun:
        return self._require_run(run_id)


def _identity_snapshot_from_request(request: dict[str, Any], model_policy_payload: Any) -> IdentitySnapshot | None:
    return (
        IdentitySnapshot.from_mapping(request.get("identity_snapshot"))
        or IdentitySnapshot.from_mapping(model_policy_payload if isinstance(model_policy_payload, dict) else None)
    )


def _tenant_id_for_run(run: AgentRun) -> str | None:
    if run.identity_snapshot is None:
        return None
    return run.identity_snapshot.tenant_id


class _RepositoryRuntimeTransactionFactory(IRuntimeTransactionFactory):
    def __init__(
        self,
        *,
        run_repository: IRunRepository,
        event_repository: IEventRepository,
        artifact_repository: IArtifactRepository,
        approval_repository: IApprovalRepository,
    ) -> None:
        self._runs = run_repository
        self._events = event_repository
        self._artifacts = artifact_repository
        self._approvals = approval_repository

    def begin(self) -> IRuntimeTransaction:
        return _RepositoryRuntimeTransaction(
            run_repository=self._runs,
            event_repository=self._events,
            artifact_repository=self._artifacts,
            approval_repository=self._approvals,
        )


class _RepositoryRuntimeTransaction(IRuntimeTransaction):
    def __init__(
        self,
        *,
        run_repository: IRunRepository,
        event_repository: IEventRepository,
        artifact_repository: IArtifactRepository,
        approval_repository: IApprovalRepository,
    ) -> None:
        self._runs = run_repository
        self._events = event_repository
        self._artifacts = artifact_repository
        self._approvals = approval_repository

    def save_run(self, run: AgentRun) -> None:
        self._runs.save(run)

    def append_event(self, event: AgentEvent) -> AgentEvent:
        return self._events.append(event, tenant_id=_tenant_id_for_event_run(event, self._runs))

    def save_artifact(self, artifact: Any) -> None:
        self._artifacts.save(artifact, tenant_id=_tenant_id_for_repository_run(artifact.run_id, self._runs))

    def save_approval(self, approval: Any) -> None:
        self._approvals.save(approval, tenant_id=_tenant_id_for_repository_run(approval.run_id, self._runs))

    def stage_outbox(self, event: AgentEvent) -> None:
        return None

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None


def _tenant_id_for_event_run(event: AgentEvent, runs: IRunRepository) -> str | None:
    return _tenant_id_for_repository_run(event.run_id, runs)


def _tenant_id_for_repository_run(run_id: str, runs: IRunRepository) -> str | None:
    run = runs.get(run_id)
    if run is None:
        return None
    return _tenant_id_for_run(run)

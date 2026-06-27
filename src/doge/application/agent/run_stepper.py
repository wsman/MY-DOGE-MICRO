"""Run step execution service."""

from __future__ import annotations

from typing import Any

from doge.application.agent.artifact_finalizer import ArtifactFinalizer
from doge.application.agent.context_builder import ContextBuilder
from doge.application.agent.model_response_assembler import ModelResponseAssembler
from doge.application.agent.runtime_args import tenant_id_for_run, tool_safe_error_payload
from doge.application.agent.transition_recorder import TransitionRecorder
from doge.core.domain.agent_models import AgentRun, EventType, RunStatus
from doge.core.domain.run_execution_context import RunExecutionContext
from doge.core.ports.agent_repository import (
    IApprovalRepository,
    IArtifactRepository,
    IEventRepository,
    IRunRepository,
)
from doge.core.ports.runtime_services import IModelExecutionService, IToolExecutionService


class RunStepper:
    """Execute one model/tool round for a run and record the resulting transition."""

    def __init__(
        self,
        *,
        run_repository: IRunRepository,
        event_repository: IEventRepository,
        artifact_repository: IArtifactRepository,
        approval_repository: IApprovalRepository,
        context_builder: ContextBuilder,
        response_assembler: ModelResponseAssembler,
        model_execution_service: IModelExecutionService,
        tool_execution_service: IToolExecutionService,
        artifact_finalizer: ArtifactFinalizer,
        transition_recorder: TransitionRecorder,
    ) -> None:
        self._runs = run_repository
        self._events = event_repository
        self._artifacts = artifact_repository
        self._approvals = approval_repository
        self._context_builder = context_builder
        self._response_assembler = response_assembler
        self._model_execution = model_execution_service
        self._tool_execution = tool_execution_service
        self._artifact_finalizer = artifact_finalizer
        self._recorder = transition_recorder

    async def step(self, run_id: str, *, tenant_id: str | None = None) -> AgentRun:
        run = self._require_run(run_id, tenant_id=tenant_id)
        if run.status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}:
            return self._hydrate(run, tenant_id=tenant_id)
        if run.status == RunStatus.CANCELLING:
            await self._recorder.mark_cancelled(run)
            return self._hydrate(run, tenant_id=tenant_id)

        await self._recorder.record(run, status=RunStatus.RUNNING)
        run = self._require_run(run_id, tenant_id=tenant_id)
        execution_context = RunExecutionContext.from_run(run)
        policy = execution_context.model_policy
        effective_tenant_id = tenant_id or tenant_id_for_run(run)
        enterprise_context = execution_context.enterprise_context
        events = self._events.list_for_run(run.run_id, tenant_id=effective_tenant_id)
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
        run = self._require_run(run_id, tenant_id=tenant_id)
        if run.status == RunStatus.CANCELLING:
            await self._recorder.mark_cancelled(run)
            return self._hydrate(run, tenant_id=tenant_id)
        if response is None:
            await self._recorder.mark_failed(run, "model unavailable", code="model_unavailable")
            return self._hydrate(run, tenant_id=tenant_id)

        await self._recorder.record(
            run,
            events=[(EventType.MODEL_RESPONSE, {
                "message": response.message.to_api_dict(),
                "finish_reason": response.finish_reason,
                "usage": response.usage or {},
                "routing": model_result.routing_payload,
            })],
        )
        if model_result.budget_exceeded:
            await self._recorder.mark_failed(run, "run budget exceeded", code="run_budget_exceeded")
            return self._hydrate(run, tenant_id=tenant_id)

        if response.message.tool_calls:
            for call in response.message.tool_calls:
                run = self._require_run(run_id, tenant_id=tenant_id)
                if run.status == RunStatus.CANCELLING:
                    await self._recorder.mark_cancelled(run)
                    return self._hydrate(run, tenant_id=tenant_id)
                function = call.get("function", {})
                name = function.get("name", "")
                arguments = function.get("arguments", "{}")
                await self._recorder.record(run, events=[(EventType.TOOL_CALL, {"tool_call": call})])
                timeout = policy.tool_timeout_seconds
                result = await self._tool_execution.execute(
                    context=enterprise_context,
                    tool_name=name,
                    arguments=arguments,
                    run_id=run.run_id,
                    timeout_seconds=float(timeout) if timeout else None,
                    request_id=execution_context.request_id,
                )
                run = self._require_run(run_id, tenant_id=tenant_id)
                if run.status == RunStatus.CANCELLING:
                    await self._recorder.mark_cancelled(run)
                    return self._hydrate(run, tenant_id=tenant_id)
                result_payload: dict[str, Any] = {
                    "ok": result.ok,
                    "name": result.name,
                    "data": result.data,
                    "error": result.error,
                }
                safe_error = tool_safe_error_payload(result)
                if safe_error is not None:
                    result_payload["safe_error"] = safe_error
                await self._recorder.record(
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
                    await self._recorder.record(
                        run,
                        status=RunStatus.AWAITING_APPROVAL,
                        approvals=[approval],
                        events=[(EventType.APPROVAL_REQUESTED, {
                            "approval_id": approval.approval_id,
                            "action": approval.action,
                            "risk_level": approval.risk_level,
                        })],
                    )
                    return self._hydrate(run, tenant_id=tenant_id)
            await self._recorder.record(run, status=RunStatus.RUNNING)
            return self._hydrate(run, tenant_id=tenant_id)

        content = self._artifact_finalizer.build_artifact(
            run,
            response.message.content,
            self._events.list_for_run(run.run_id, tenant_id=effective_tenant_id),
            usage=response.usage or {},
        )
        await self._recorder.record(
            run,
            status=RunStatus.COMPLETED,
            artifacts=[content],
            events=[(EventType.ARTIFACT_CREATED, {
                "artifact_id": content.artifact_id,
                "kind": content.kind,
                "title": content.title,
            })],
        )
        return self._hydrate(run, tenant_id=tenant_id)

    def _require_run(self, run_id: str, *, tenant_id: str | None = None) -> AgentRun:
        get_header = getattr(self._runs, "get_run_header", None)
        run = get_header(run_id, tenant_id=tenant_id) if get_header is not None else self._runs.get(run_id, tenant_id=tenant_id)
        if run is None:
            raise KeyError(f"run not found: {run_id}")
        return run

    def _hydrate(self, run: AgentRun, *, tenant_id: str | None = None) -> AgentRun:
        run.events = self._events.list_for_run(run.run_id, tenant_id=tenant_id)
        run.artifacts = self._artifacts.list_for_run(run.run_id, tenant_id=tenant_id)
        run.approvals = self._approvals.list_for_run(run.run_id, tenant_id=tenant_id)
        return run

"""Run step execution service."""

from __future__ import annotations

from typing import Any

from doge.application.agent.artifact_finalizer import ArtifactFinalizer
from doge.application.agent.context_builder import ContextBuilder
from doge.application.agent.model_response_assembler import ModelResponseAssembler
from doge.application.agent.runtime_args import tool_safe_error_payload
from doge.application.agent.transition_recorder import TransitionRecorder
from doge.core.domain.agent_models import AgentRun, EventType, RunStatus
from doge.core.domain.evidence_chunk_models import EvidenceChunk
from doge.core.domain.run_execution_context import RunExecutionContext
from doge.core.ports.agent_repository import (
    IApprovalRepository,
    IArtifactRepository,
    IEventRepository,
    IRunRepository,
)
from doge.core.ports.runtime_services import IModelExecutionService, IToolExecutionService, ToolResult
from doge.shared.scope import TenantScope


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
        citation_assembler: Any | None = None,
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
        self._citation_assembler = citation_assembler

    async def step(self, scope: TenantScope, run_id: str) -> AgentRun:
        run = self._require_run(scope, run_id)
        if run.status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}:
            self._cleanup_tool_results(run.run_id)
            return self._hydrate(scope, run)
        if run.status == RunStatus.CANCELLING:
            await self._recorder.mark_cancelled(run)
            self._cleanup_tool_results(run.run_id)
            return self._hydrate(scope, run)

        await self._recorder.record(run, status=RunStatus.RUNNING)
        run = self._require_run(scope, run_id)
        execution_context = RunExecutionContext.from_run(run)
        policy = execution_context.model_policy
        enterprise_context = execution_context.enterprise_context
        events = self._events.list_for_run(run.run_id, tenant_id=scope.tenant_id)
        tool_results = _tool_results_from_events(events)
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
        run = self._require_run(scope, run_id)
        if run.status == RunStatus.CANCELLING:
            await self._recorder.mark_cancelled(run)
            self._cleanup_tool_results(run.run_id)
            return self._hydrate(scope, run)
        if response is None:
            await self._recorder.mark_failed(run, "model unavailable", code="model_unavailable")
            self._cleanup_tool_results(run.run_id)
            return self._hydrate(scope, run)

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
            self._cleanup_tool_results(run.run_id)
            return self._hydrate(scope, run)

        if response.message.tool_calls:
            for call in response.message.tool_calls:
                run = self._require_run(scope, run_id)
                if run.status == RunStatus.CANCELLING:
                    await self._recorder.mark_cancelled(run)
                    self._cleanup_tool_results(run.run_id)
                    return self._hydrate(scope, run)
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
                tool_results.append(result)
                run = self._require_run(scope, run_id)
                if run.status == RunStatus.CANCELLING:
                    await self._recorder.mark_cancelled(run)
                    self._cleanup_tool_results(run.run_id)
                    return self._hydrate(scope, run)
                result_payload: dict[str, Any] = {
                    "ok": result.ok,
                    "name": result.name,
                    "data": result.data,
                    "error": result.error,
                }
                safe_error = tool_safe_error_payload(result)
                if safe_error is not None:
                    result_payload["safe_error"] = safe_error
                if result.evidence_refs is not None:
                    result_payload["evidence_refs"] = [ref.to_dict() if hasattr(ref, "to_dict") else ref for ref in result.evidence_refs]
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
                        why_needed=result.data.get("why_needed", ""),
                        impact=result.data.get("impact", ""),
                        deny_consequence=result.data.get("deny_consequence", ""),
                        publish_target=result.data.get("publish_target", ""),
                    )
                    await self._recorder.record(
                        run,
                        status=RunStatus.AWAITING_APPROVAL,
                        approvals=[approval],
                        events=[(EventType.APPROVAL_REQUESTED, {
                            "approval_id": approval.approval_id,
                            "action": approval.action,
                            "risk_level": approval.risk_level,
                            "why_needed": approval.why_needed,
                            "impact": approval.impact,
                            "deny_consequence": approval.deny_consequence,
                            "publish_target": approval.publish_target,
                        })],
                    )
                    return self._hydrate(scope, run)
            await self._recorder.record(run, status=RunStatus.RUNNING)
            return self._hydrate(scope, run)

        citation_data = None
        if self._citation_assembler is not None:
            try:
                cited_artifact = self._citation_assembler.assemble(
                    run=run,
                    content=response.message.content or "",
                    tool_results=tool_results,
                )
                citation_data = cited_artifact.data
                # Use the enriched content from the assembler
                content = cited_artifact.content
            except Exception:
                # Fallback: use original content without citations
                content = response.message.content or ""
        else:
            content = response.message.content or ""

        artifact = self._artifact_finalizer.build_artifact(
            run,
            content,
            self._events.list_for_run(run.run_id, tenant_id=scope.tenant_id),
            usage=response.usage or {},
            citation_data=citation_data,
        )
        await self._recorder.record(
            run,
            status=RunStatus.COMPLETED,
            artifacts=[artifact],
            events=[(EventType.ARTIFACT_CREATED, {
                "artifact_id": artifact.artifact_id,
                "kind": artifact.kind,
                "title": artifact.title,
            })],
        )
        # Clean up accumulated tool results for this run
        self._cleanup_tool_results(run.run_id)
        return self._hydrate(scope, run)

    def _cleanup_tool_results(self, run_id: str) -> None:
        return None

    def _require_run(self, scope: TenantScope, run_id: str) -> AgentRun:
        get_header = getattr(self._runs, "get_run_header", None)
        run = get_header(run_id, tenant_id=scope.tenant_id) if get_header is not None else self._runs.get(run_id, tenant_id=scope.tenant_id)
        if run is None:
            raise KeyError(f"run not found: {run_id}")
        return run

    def _hydrate(self, scope: TenantScope, run: AgentRun) -> AgentRun:
        run.events = self._events.list_for_run(run.run_id, tenant_id=scope.tenant_id)
        run.artifacts = self._artifacts.list_for_run(run.run_id, tenant_id=scope.tenant_id)
        run.approvals = self._approvals.list_for_run(run.run_id, tenant_id=scope.tenant_id)
        return run


def _tool_results_from_events(events: list[Any]) -> list[ToolResult]:
    """Rebuild persisted tool results for restart-safe artifact assembly."""
    results: list[ToolResult] = []
    for event in sorted(events, key=lambda item: getattr(item, "sequence", 0)):
        if event.event_type != EventType.TOOL_RESULT:
            continue
        result = _tool_result_from_event(event)
        if result is not None:
            results.append(result)
    return results


def _tool_result_from_event(event: Any) -> ToolResult | None:
    payload = getattr(event, "payload", {}) or {}
    result_payload = payload.get("result") or {}
    if not isinstance(result_payload, dict):
        return None
    data = result_payload.get("data")
    if data is None:
        data = {}
    elif not isinstance(data, dict):
        data = {"value": data}
    return ToolResult(
        name=str(result_payload.get("name") or payload.get("name") or ""),
        data=data,
        ok=bool(result_payload.get("ok", True)),
        error=result_payload.get("error"),
        safe_error=result_payload.get("safe_error"),
        evidence_refs=_evidence_refs_from_payload(result_payload.get("evidence_refs")),
    )


def _evidence_refs_from_payload(value: Any) -> list[EvidenceChunk] | None:
    if not isinstance(value, list):
        return None
    refs: list[EvidenceChunk] = []
    for item in value:
        if isinstance(item, EvidenceChunk):
            refs.append(item)
            continue
        if not isinstance(item, dict):
            continue
        try:
            refs.append(EvidenceChunk.from_mapping(item))
        except (KeyError, TypeError, ValueError):
            continue
    return refs or None

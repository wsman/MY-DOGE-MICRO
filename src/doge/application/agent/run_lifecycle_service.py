"""Run lifecycle service."""

from __future__ import annotations

from typing import Any

from doge.application.agent.runtime_args import (
    failure_args,
    identity_snapshot_from_request,
    queue_args,
    run_args,
)
from doge.application.agent.run_stepper import RunStepper
from doge.application.agent.transition_recorder import TransitionRecorder
from doge.core.domain.agent_models import AgentRun, EventType, RunStatus, utc_now
from doge.core.domain.model_policy import ModelPolicy
from doge.core.ports.agent_repository import (
    IApprovalRepository,
    IArtifactRepository,
    IEventRepository,
    IRunRepository,
)
from doge.shared.scope import TenantScope


class RunLifecycleService:
    """Own run creation, execution loop, queueing, cancellation, and failure recording."""

    def __init__(
        self,
        *,
        run_repository: IRunRepository,
        event_repository: IEventRepository,
        artifact_repository: IArtifactRepository,
        approval_repository: IApprovalRepository,
        transition_recorder: TransitionRecorder,
        run_stepper: RunStepper,
    ) -> None:
        self._runs = run_repository
        self._events = event_repository
        self._artifacts = artifact_repository
        self._approvals = approval_repository
        self._recorder = transition_recorder
        self._stepper = run_stepper

    async def create_run(self, request: dict[str, Any], *, tenant_id: str | None = None) -> AgentRun:
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
            workflow_context=request.get("workflow_context"),
            identity_snapshot=identity_snapshot_from_request(request, model_policy_payload),
        )
        payload = {"question": run.question, "workflow": run.workflow}
        template = request.get("template")
        if isinstance(template, dict):
            payload["template"] = template
        await self._recorder.record(run, events=[(EventType.RUN_CREATED, payload)], save_run=True)
        return self._hydrate(run, tenant_id=tenant_id)

    async def run_to_pause_or_completion(self, run_id: str, *, tenant_id: str | None = None) -> AgentRun:
        run = self._require_run(run_id, tenant_id=tenant_id)
        policy = ModelPolicy.from_dict(run.model_policy)
        max_rounds = policy.max_tool_rounds
        for _ in range(max_rounds):
            run = await self._stepper.step(run_id, tenant_id=tenant_id)
            if run.status in {
                RunStatus.AWAITING_APPROVAL,
                RunStatus.CANCELLED,
                RunStatus.COMPLETED,
                RunStatus.FAILED,
            }:
                return run
        run = self._require_run(run_id, tenant_id=tenant_id)
        await self._recorder.mark_failed(run, "max tool rounds exceeded", code="max_tool_rounds_exceeded")
        return self._hydrate(run, tenant_id=tenant_id)

    async def queue_run(
        self,
        scope: TenantScope | str | None,
        run_id: str | None = None,
        reason: str = "queued",
        *,
        tenant_id: str | None = None,
    ) -> AgentRun:
        resolved_scope, resolved_run_id, resolved_reason = queue_args(scope, run_id, reason, tenant_id=tenant_id)
        run = self._require_run(resolved_run_id, tenant_id=resolved_scope.tenant_id)
        if run.status == RunStatus.QUEUED:
            return self._hydrate(run, tenant_id=resolved_scope.tenant_id)
        if run.status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}:
            return self._hydrate(run, tenant_id=resolved_scope.tenant_id)
        await self._recorder.record(
            run,
            status=RunStatus.QUEUED,
            events=[(EventType.RUN_QUEUED, {"reason": resolved_reason})],
        )
        return self._hydrate(run, tenant_id=resolved_scope.tenant_id)

    async def cancel_run(
        self,
        scope: TenantScope | str | None,
        run_id: str | None = None,
        *,
        tenant_id: str | None = None,
    ) -> AgentRun:
        resolved_scope, resolved_run_id = run_args(scope, run_id, tenant_id=tenant_id)
        run = self._require_run(resolved_run_id, tenant_id=resolved_scope.tenant_id)
        if run.status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}:
            return self._hydrate(run, tenant_id=resolved_scope.tenant_id)
        run.cancel_requested_at = utc_now()
        if run.status != RunStatus.CANCELLING:
            await self._recorder.record(run, status=RunStatus.CANCELLING)
            run = self._require_run(resolved_run_id, tenant_id=resolved_scope.tenant_id)
        else:
            await self._recorder.record(run, save_run=True)
        return self._hydrate(run, tenant_id=resolved_scope.tenant_id)

    async def finalize_cancelled(
        self,
        scope: TenantScope | str | None,
        run_id: str | None = None,
        *,
        tenant_id: str | None = None,
    ) -> AgentRun:
        resolved_scope, resolved_run_id = run_args(scope, run_id, tenant_id=tenant_id)
        run = self._require_run(resolved_run_id, tenant_id=resolved_scope.tenant_id)
        if run.status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}:
            return self._hydrate(run, tenant_id=resolved_scope.tenant_id)
        await self._recorder.mark_cancelled(run)
        return self._hydrate(run, tenant_id=resolved_scope.tenant_id)

    async def record_failure(
        self,
        scope: TenantScope | str | None,
        run_id: str | None = None,
        message: str | None = None,
        *,
        tenant_id: str | None = None,
    ) -> AgentRun:
        resolved_scope, resolved_run_id, _raw_message = failure_args(scope, run_id, message, tenant_id=tenant_id)
        run = self._require_run(resolved_run_id, tenant_id=resolved_scope.tenant_id)
        if run.status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}:
            return run
        await self._recorder.mark_failed(run, "runtime failure", code="runtime_failure")
        return self._hydrate(run, tenant_id=resolved_scope.tenant_id)

    def get_run(
        self,
        scope: TenantScope | str | None,
        run_id: str | None = None,
        *,
        tenant_id: str | None = None,
    ) -> AgentRun | None:
        resolved_scope, resolved_run_id = run_args(scope, run_id, tenant_id=tenant_id)
        run = self._require_run_header_or_none(resolved_run_id, tenant_id=resolved_scope.tenant_id)
        if run is None:
            return None
        return self._hydrate(run, tenant_id=resolved_scope.tenant_id)

    def list_events(
        self,
        scope: TenantScope | str | None,
        run_id: str | None = None,
        *,
        tenant_id: str | None = None,
    ) -> list:
        resolved_scope, resolved_run_id = run_args(scope, run_id, tenant_id=tenant_id)
        return self._events.list_for_run(resolved_run_id, tenant_id=resolved_scope.tenant_id)

    def list_runs(
        self,
        scope: TenantScope | str | None = None,
        session_id: str | None = None,
        limit: int = 20,
        *,
        tenant_id: str | None = None,
    ) -> list:
        from doge.application.agent.runtime_args import list_runs_args

        resolved_scope, resolved_session_id = list_runs_args(scope, session_id, tenant_id=tenant_id)
        if resolved_session_id:
            return self._runs.list_by_session(resolved_session_id, tenant_id=resolved_scope.tenant_id)
        return self._runs.list_recent(limit, tenant_id=resolved_scope.tenant_id)

    def list_artifacts(
        self,
        scope: TenantScope | str | None,
        run_id: str | None = None,
        *,
        tenant_id: str | None = None,
    ):
        resolved_scope, resolved_run_id = run_args(scope, run_id, tenant_id=tenant_id)
        return self._artifacts.list_for_run(resolved_run_id, tenant_id=resolved_scope.tenant_id)

    def _require_run(self, run_id: str, *, tenant_id: str | None = None) -> AgentRun:
        run = self._require_run_header_or_none(run_id, tenant_id=tenant_id)
        if run is None:
            raise KeyError(f"run not found: {run_id}")
        return run

    def _require_run_header_or_none(self, run_id: str, *, tenant_id: str | None = None) -> AgentRun | None:
        get_header = getattr(self._runs, "get_run_header", None)
        if get_header is not None:
            return get_header(run_id, tenant_id=tenant_id)
        return self._runs.get(run_id, tenant_id=tenant_id)

    def _hydrate(self, run: AgentRun, *, tenant_id: str | None = None) -> AgentRun:
        run.events = self._events.list_for_run(run.run_id, tenant_id=tenant_id)
        run.artifacts = self._artifacts.list_for_run(run.run_id, tenant_id=tenant_id)
        run.approvals = self._approvals.list_for_run(run.run_id, tenant_id=tenant_id)
        return run

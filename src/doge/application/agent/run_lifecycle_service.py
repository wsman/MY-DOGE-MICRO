"""Run lifecycle service."""

from __future__ import annotations

from typing import Any

from doge.application.agent.runtime_args import (
    identity_snapshot_from_request,
    request_for_scope,
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

    async def create_run(self, scope: TenantScope, request: dict[str, Any]) -> AgentRun:
        request = request_for_scope(scope, request)
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
        return self._hydrate(scope, run)

    async def run_to_pause_or_completion(self, scope: TenantScope, run_id: str) -> AgentRun:
        run = self._require_run(scope, run_id)
        policy = ModelPolicy.from_dict(run.model_policy)
        max_rounds = policy.max_tool_rounds
        for _ in range(max_rounds):
            run = await self._stepper.step(scope, run_id)
            if run.status in {
                RunStatus.AWAITING_APPROVAL,
                RunStatus.CANCELLED,
                RunStatus.COMPLETED,
                RunStatus.FAILED,
            }:
                return run
        run = self._require_run(scope, run_id)
        await self._recorder.mark_failed(run, "max tool rounds exceeded", code="max_tool_rounds_exceeded")
        return self._hydrate(scope, run)

    async def queue_run(
        self,
        scope: TenantScope,
        run_id: str,
        reason: str = "queued",
    ) -> AgentRun:
        run = self._require_run(scope, run_id)
        if run.status == RunStatus.QUEUED:
            return self._hydrate(scope, run)
        if run.status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}:
            return self._hydrate(scope, run)
        await self._recorder.record(
            run,
            status=RunStatus.QUEUED,
            events=[(EventType.RUN_QUEUED, {"reason": reason})],
        )
        return self._hydrate(scope, run)

    async def resume_run(
        self,
        scope: TenantScope,
        run_id: str,
    ) -> AgentRun:
        run = self._require_run(scope, run_id)
        if run.status == RunStatus.RUNNING:
            return self._hydrate(scope, run)
        if run.status == RunStatus.AWAITING_APPROVAL:
            raise ValueError("run is awaiting approval; pass approval_id to resume")
        if run.status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED, RunStatus.CANCELLING}:
            raise ValueError(f"run is not resumable from status: {run.status.value}")
        return await self.run_to_pause_or_completion(scope, run_id)

    async def cancel_run(
        self,
        scope: TenantScope,
        run_id: str,
    ) -> AgentRun:
        run = self._require_run(scope, run_id)
        if run.status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}:
            return self._hydrate(scope, run)
        run.cancel_requested_at = utc_now()
        if run.status != RunStatus.CANCELLING:
            await self._recorder.record(run, status=RunStatus.CANCELLING)
            run = self._require_run(scope, run_id)
        else:
            await self._recorder.record(run, save_run=True)
        return self._hydrate(scope, run)

    async def finalize_cancelled(
        self,
        scope: TenantScope,
        run_id: str,
    ) -> AgentRun:
        run = self._require_run(scope, run_id)
        if run.status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}:
            return self._hydrate(scope, run)
        await self._recorder.mark_cancelled(run)
        return self._hydrate(scope, run)

    async def record_failure(
        self,
        scope: TenantScope,
        run_id: str,
        message: str,
    ) -> AgentRun:
        run = self._require_run(scope, run_id)
        if run.status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}:
            return run
        await self._recorder.mark_failed(run, "runtime failure", code="runtime_failure")
        return self._hydrate(scope, run)

    def get_run(
        self,
        scope: TenantScope,
        run_id: str,
    ) -> AgentRun | None:
        run = self._require_run_header_or_none(scope, run_id)
        if run is None:
            return None
        return self._hydrate(scope, run)

    def list_events(
        self,
        scope: TenantScope,
        run_id: str,
    ) -> list:
        return self._events.list_for_run(run_id, tenant_id=scope.tenant_id)

    def list_runs(
        self,
        scope: TenantScope,
        session_id: str | None = None,
        limit: int = 20,
    ) -> list:
        if session_id:
            return self._runs.list_by_session(session_id, limit=limit, tenant_id=scope.tenant_id)
        return self._runs.list_recent(limit, tenant_id=scope.tenant_id)

    def list_artifacts(
        self,
        scope: TenantScope,
        run_id: str,
    ):
        return self._artifacts.list_for_run(run_id, tenant_id=scope.tenant_id)

    def _require_run(self, scope: TenantScope, run_id: str) -> AgentRun:
        run = self._require_run_header_or_none(scope, run_id)
        if run is None:
            raise KeyError(f"run not found: {run_id}")
        return run

    def _require_run_header_or_none(self, scope: TenantScope, run_id: str) -> AgentRun | None:
        get_header = getattr(self._runs, "get_run_header", None)
        if get_header is not None:
            return get_header(run_id, tenant_id=scope.tenant_id)
        return self._runs.get(run_id, tenant_id=scope.tenant_id)

    def _hydrate(self, scope: TenantScope, run: AgentRun) -> AgentRun:
        run.events = self._events.list_for_run(run.run_id, tenant_id=scope.tenant_id)
        run.artifacts = self._artifacts.list_for_run(run.run_id, tenant_id=scope.tenant_id)
        run.approvals = self._approvals.list_for_run(run.run_id, tenant_id=scope.tenant_id)
        return run

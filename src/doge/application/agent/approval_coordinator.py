"""Approval coordination service for runtime runs."""

from __future__ import annotations

from doge.application.agent.runtime_args import approval_args
from doge.application.agent.transition_recorder import TransitionRecorder
from doge.core.domain.agent_models import AgentRun, EventType, RunStatus, utc_now
from doge.core.ports.agent_repository import IApprovalRepository, IRunRepository
from doge.shared.scope import TenantScope


class ApprovalCoordinator:
    """Resolve approvals and transition the run to the appropriate next state."""

    def __init__(
        self,
        *,
        run_repository: IRunRepository,
        approval_repository: IApprovalRepository,
        transition_recorder: TransitionRecorder,
    ) -> None:
        self._runs = run_repository
        self._approvals = approval_repository
        self._recorder = transition_recorder

    async def resolve(
        self,
        scope: TenantScope | str | None,
        run_id: str | None,
        approval_id: str | bool | None,
        approved: bool,
        *,
        tenant_id: str | None = None,
    ) -> AgentRun:
        resolved_scope, resolved_run_id, resolved_approval_id, resolved_approved = approval_args(
            scope,
            run_id,
            approval_id,
            approved,
            tenant_id=tenant_id,
        )
        run = self._require_run(resolved_run_id, tenant_id=resolved_scope.tenant_id)
        approval = self._approvals.get(resolved_approval_id, tenant_id=resolved_scope.tenant_id)
        if approval is None or approval.run_id != resolved_run_id:
            raise KeyError(f"approval not found: {resolved_approval_id}")
        approval.status = "approved" if resolved_approved else "denied"
        approval.resolved_at = utc_now()
        if not resolved_approved:
            await self._recorder.record(
                run,
                status=RunStatus.FAILED,
                approvals=[approval],
                events=[(EventType.APPROVAL_RESOLVED, {
                    "approval_id": resolved_approval_id,
                    "approved": resolved_approved,
                })],
            )
            return run
        await self._recorder.record(
            run,
            status=RunStatus.QUEUED,
            approvals=[approval],
            events=[
                (EventType.APPROVAL_RESOLVED, {
                    "approval_id": resolved_approval_id,
                    "approved": resolved_approved,
                }),
                (EventType.RUN_QUEUED, {"reason": "approval_resolved"}),
            ],
        )
        return run

    def _require_run(self, run_id: str, *, tenant_id: str | None = None) -> AgentRun:
        get_header = getattr(self._runs, "get_run_header", None)
        run = get_header(run_id, tenant_id=tenant_id) if get_header is not None else self._runs.get(run_id, tenant_id=tenant_id)
        if run is None:
            raise KeyError(f"run not found: {run_id}")
        return run

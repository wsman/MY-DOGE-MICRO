"""Approval coordination service for runtime runs."""

from __future__ import annotations

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
        scope: TenantScope,
        run_id: str,
        approval_id: str,
        approved: bool,
    ) -> AgentRun:
        run = self._require_run(scope, run_id)
        approval = self._approvals.get(approval_id, tenant_id=scope.tenant_id)
        if approval is None or approval.run_id != run_id:
            raise KeyError(f"approval not found: {approval_id}")
        approval.status = "approved" if approved else "denied"
        approval.resolved_at = utc_now()
        if not approved:
            await self._recorder.record(
                run,
                status=RunStatus.FAILED,
                approvals=[approval],
                events=[(EventType.APPROVAL_RESOLVED, {
                    "approval_id": approval_id,
                    "approved": approved,
                })],
            )
            return run
        await self._recorder.record(
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
        return run

    def _require_run(self, scope: TenantScope, run_id: str) -> AgentRun:
        get_header = getattr(self._runs, "get_run_header", None)
        run = get_header(run_id, tenant_id=scope.tenant_id) if get_header is not None else self._runs.get(run_id, tenant_id=scope.tenant_id)
        if run is None:
            raise KeyError(f"run not found: {run_id}")
        return run

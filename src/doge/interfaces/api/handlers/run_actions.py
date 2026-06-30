"""Run action API handlers without FastAPI dependencies."""

from __future__ import annotations

from doge.core.ports.enterprise_governance import ApprovalActorDecision, EnterpriseAuditEvent
from doge.interfaces.api.handlers.queries import GetRunHandler, RunAccessContext


class CancelRunHandler:
    def __init__(self, *, worker, runtime=None) -> None:
        self._worker = worker
        self._runtime = runtime

    async def handle(self, *, run_id: str, scope=None, access: RunAccessContext | None = None):
        access = access or RunAccessContext(scope=scope)
        if self._runtime is not None:
            GetRunHandler(runtime=self._runtime).handle(run_id=run_id, access=access)
        return await self._worker.cancel_run(run_id, scope=access.scope)


class ResolveApprovalHandler:
    def __init__(self, *, worker, runtime=None, governance=None) -> None:
        self._worker = worker
        self._runtime = runtime
        self._governance = governance

    async def handle(
        self,
        *,
        run_id: str,
        approval_id: str,
        approved: bool,
        scope=None,
        access: RunAccessContext | None = None,
    ):
        access = access or RunAccessContext(scope=scope)
        if self._runtime is not None:
            GetRunHandler(runtime=self._runtime).handle(run_id=run_id, access=access)
        self._ensure_approval_authority(access, approval_id)
        run = await self._worker.resolve_approval(
            run_id,
            approval_id,
            approved,
            scope=access.scope,
        )
        self._record_approval_actor(access, approval_id, run_id, approved)
        return run

    def _ensure_approval_authority(self, access: RunAccessContext, approval_id: str) -> None:
        if not access.is_enterprise:
            return
        context = access.enterprise_context
        if self._governance and self._governance.is_allowed(
            context,
            "approval",
            approval_id,
            "approve",
        ):
            return
        if "*" in context.approval_authority or approval_id in context.approval_authority:
            return
        raise PermissionError("approval access denied")

    def _record_approval_actor(
        self,
        access: RunAccessContext,
        approval_id: str,
        run_id: str,
        approved: bool,
    ) -> None:
        if not access.is_enterprise or self._governance is None:
            return
        context = access.enterprise_context
        self._governance.record_approval_decision(
            ApprovalActorDecision(
                approval_id=approval_id,
                run_id=run_id,
                tenant_id=context.tenant_id,
                actor_hash=context.user_hash,
                request_id=access.request_id,
                authority_source="enterprise_context",
                decision="approved" if approved else "rejected",
                metadata={"approval_authority": sorted(context.approval_authority)},
            )
        )
        self._governance.append_audit_event(
            EnterpriseAuditEvent(
                tenant_id=context.tenant_id,
                actor_hash=context.user_hash,
                event_type="approval_decision",
                resource_type="approval",
                resource_id=approval_id,
                request_id=access.request_id,
                metadata={"run_id": run_id, "approved": approved},
            )
        )


class ResumeRunHandler:
    def __init__(self, *, runtime, governance=None) -> None:
        self._runtime = runtime
        self._governance = governance

    async def handle(
        self,
        *,
        run_id: str,
        approval_id: str | None = None,
        approved: bool = True,
        scope=None,
        access: RunAccessContext | None = None,
    ):
        access = access or RunAccessContext(scope=scope)
        GetRunHandler(runtime=self._runtime).handle(run_id=run_id, access=access)
        if approval_id is not None:
            approval_handler = ResolveApprovalHandler(
                worker=None,
                runtime=self._runtime,
                governance=self._governance,
            )
            approval_handler._ensure_approval_authority(access, approval_id)
            run = await self._runtime.resolve_approval_and_resume(
                access.scope,
                run_id,
                approval_id,
                approved,
            )
            approval_handler._record_approval_actor(access, approval_id, run_id, approved)
            return run
        return await self._runtime.resume_run(access.scope, run_id)

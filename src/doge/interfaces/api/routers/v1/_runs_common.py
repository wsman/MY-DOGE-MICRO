"""Shared helpers for the focused v1 run sub-routers.

Extracts the request-scope/authorization/summary-redaction logic out of the
route handlers so ``runs.py`` can shrink to a compatibility aggregator and the
queries/actions/stream routers stay focused. These helpers are a step toward
application-layer run services; the worker call surface itself remains in the
actions router (introducing run/approval command services is gated separately).
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request

from doge.application.use_cases.run_summary import BuildRunSummary, redact_inaccessible_citations
from doge.core.domain.agent_models import AgentRun, RunStatus
from doge.core.ports.agent_runtime import IResearchAgentRuntime
from doge.core.ports.enterprise_governance import IEnterpriseGovernanceRepository
from doge.interfaces.api import deps
from doge.interfaces.api.enterprise_access import (
    enterprise_context,
    filter_accessible_resource_ids,
    is_enterprise_request,
)
from doge.shared.scope import TenantScope

STREAM_CLOSE_STATUSES = {
    RunStatus.AWAITING_APPROVAL,
    RunStatus.COMPLETED,
    RunStatus.FAILED,
    RunStatus.CANCELLED,
}
STREAM_CLOSE_EVENTS = {
    "approval_requested",
    "artifact_created",
    "error",
    "run_cancelled",
}


def require_run_summary_api(settings=Depends(deps.get_settings_dep)) -> None:
    if not settings.features.run_summary_api:
        raise HTTPException(404, "run summary API disabled")


def authorized_run(request: Request, runtime: IResearchAgentRuntime, run_id: str) -> AgentRun:
    """Return the run for ``run_id`` after tenant authorization checks."""
    run = runtime.get_run(request_scope(request), run_id)
    if run is None:
        raise HTTPException(404, "run not found")
    if is_enterprise_request(request):
        if run_tenant_id(run) != enterprise_context(request).tenant_id:
            raise HTTPException(404, "run not found")
    return run


def build_authorized_summary(
    request: Request,
    run: AgentRun,
    use_case: BuildRunSummary,
    governance: IEnterpriseGovernanceRepository,
) -> dict:
    """Build the run summary and redact citations the caller cannot read."""
    tenant_id = enterprise_context(request).tenant_id if is_enterprise_request(request) else None
    result = use_case.build(run, tenant_id=tenant_id)
    if not is_enterprise_request(request):
        return result
    document_ids = sorted(
        {
            citation["document_id"]
            for citation in result["citations"]
            if citation.get("document_id")
        }
    )
    allowed = filter_accessible_resource_ids(request, governance, "document", document_ids, "read")
    return redact_inaccessible_citations(result, allowed)


def max_event_sequence_after(
    runtime: IResearchAgentRuntime,
    run_id: str,
    after_sequence: int,
    *,
    scope: TenantScope,
) -> int:
    return max(
        (
            event.sequence
            for event in runtime.list_events(scope, run_id)
            if event.sequence > after_sequence
        ),
        default=after_sequence,
    )


def request_scope(request: Request) -> TenantScope:
    if not is_enterprise_request(request):
        return TenantScope.local()
    context = enterprise_context(request)
    return TenantScope.enterprise(context.tenant_id, context.user_hash)


def run_tenant_id(run: AgentRun) -> str | None:
    if run.identity_snapshot is not None:
        return run.identity_snapshot.tenant_id
    return None


def request_tenant_id(request: Request) -> str | None:
    if not is_enterprise_request(request):
        return None
    return enterprise_context(request).tenant_id

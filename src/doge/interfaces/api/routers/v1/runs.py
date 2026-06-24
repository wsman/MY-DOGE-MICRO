"""v1 run routes."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from doge.application.use_cases.run_summary import BuildRunSummary, redact_inaccessible_citations
from doge.application.agent.worker import AsyncioWorker
from doge.core.domain.agent_models import AgentRun, RunStatus
from doge.core.ports.agent_runtime import IResearchAgentRuntime
from doge.core.ports.enterprise_governance import IEnterpriseGovernanceRepository
from doge.core.ports.event_subscriber import IEventSubscriber
from doge.interfaces.api import deps
from doge.interfaces.api.enterprise_access import (
    append_audit,
    enterprise_context,
    ensure_approval_authority,
    filter_accessible_resource_ids,
    is_enterprise_request,
    record_approval_actor,
)
from doge.interfaces.api.routers.v1._common import serialize

router = APIRouter(dependencies=[Depends(deps.require_api_token)])
_STREAM_CLOSE_STATUSES = {
    RunStatus.AWAITING_APPROVAL,
    RunStatus.COMPLETED,
    RunStatus.FAILED,
    RunStatus.CANCELLED,
}
_STREAM_CLOSE_EVENTS = {
    "approval_requested",
    "artifact_created",
    "error",
    "run_cancelled",
}


class ApprovalRequest(BaseModel):
    approved: bool = True


def _require_run_summary_api(settings=Depends(deps.get_settings_dep)) -> None:
    if not settings.features.run_summary_api:
        raise HTTPException(404, "run summary API disabled")


@router.get("/runs/{run_id}")
async def get_run(
    request: Request,
    run_id: str,
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
):
    return serialize(_authorized_run(request, runtime, run_id))


@router.post("/runs/{run_id}/cancel", status_code=202)
async def cancel_run(
    request: Request,
    run_id: str,
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
    worker: AsyncioWorker = Depends(deps.get_daemon_worker),
):
    _authorized_run(request, runtime, run_id)
    try:
        return serialize(await worker.cancel_run(run_id))
    except KeyError:
        raise HTTPException(404, "run not found")


@router.get("/runs/{run_id}/events")
async def get_events(
    request: Request,
    run_id: str,
    after_sequence: int = 0,
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
):
    _authorized_run(request, runtime, run_id)
    events = [event for event in runtime.list_events(run_id) if event.sequence > after_sequence]
    return {"events": serialize(events)}


@router.get("/runs/{run_id}/stream")
async def stream_run(
    request: Request,
    run_id: str,
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
    subscriber: IEventSubscriber = Depends(deps.get_event_subscriber),
):
    authorized = _authorized_run(request, runtime, run_id)
    try:
        after_sequence = int(last_event_id or "0")
    except ValueError:
        after_sequence = 0

    async def generator():
        run = runtime.get_run(run_id) or authorized
        terminal_at_start = run.status in _STREAM_CLOSE_STATUSES
        initial_max_sequence = _max_event_sequence_after(runtime, run_id, after_sequence)
        if terminal_at_start and initial_max_sequence <= after_sequence:
            return
        async for event in subscriber.subscribe(run_id, after_sequence=after_sequence):
            yield {
                "id": str(event.sequence),
                "event": event.event_type.value,
                "data": json.dumps(serialize(event), ensure_ascii=False),
            }
            run = runtime.get_run(run_id)
            if run and run.status in _STREAM_CLOSE_STATUSES:
                if terminal_at_start and event.sequence >= initial_max_sequence:
                    return
                if not terminal_at_start and event.event_type.value in _STREAM_CLOSE_EVENTS:
                    return

    return EventSourceResponse(generator())


@router.get("/runs/{run_id}/artifacts")
async def get_artifacts(
    request: Request,
    run_id: str,
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
):
    _authorized_run(request, runtime, run_id)
    return {"artifacts": serialize(runtime.list_artifacts(run_id))}


@router.get("/runs/{run_id}/summary", dependencies=[Depends(_require_run_summary_api)])
async def get_run_summary(
    request: Request,
    run_id: str,
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
    use_case: BuildRunSummary = Depends(deps.get_run_summary_use_case),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    run = _authorized_run(request, runtime, run_id)
    result = _build_authorized_summary(request, run, use_case, governance)
    append_audit(request, governance, "run_summary_read", "run", run_id)
    return {"summary": serialize(result["summary"])}


@router.get("/runs/{run_id}/claims", dependencies=[Depends(_require_run_summary_api)])
async def get_run_claims(
    request: Request,
    run_id: str,
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
    use_case: BuildRunSummary = Depends(deps.get_run_summary_use_case),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    run = _authorized_run(request, runtime, run_id)
    result = _build_authorized_summary(request, run, use_case, governance)
    append_audit(request, governance, "run_claims_read", "run", run_id)
    return {
        "summary_id": result["summary"]["summary_id"],
        "claims": serialize(result["claims"]),
    }


@router.get("/runs/{run_id}/citations", dependencies=[Depends(_require_run_summary_api)])
async def get_run_citations(
    request: Request,
    run_id: str,
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
    use_case: BuildRunSummary = Depends(deps.get_run_summary_use_case),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    run = _authorized_run(request, runtime, run_id)
    result = _build_authorized_summary(request, run, use_case, governance)
    append_audit(request, governance, "run_citations_read", "run", run_id)
    return {
        "summary_id": result["summary"]["summary_id"],
        "citations": serialize(result["citations"]),
    }


@router.get("/runs/{run_id}/eval", dependencies=[Depends(_require_run_summary_api)])
async def get_run_eval(
    request: Request,
    run_id: str,
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
    use_case: BuildRunSummary = Depends(deps.get_run_summary_use_case),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    run = _authorized_run(request, runtime, run_id)
    result = _build_authorized_summary(request, run, use_case, governance)
    append_audit(request, governance, "run_eval_read", "run", run_id)
    return {
        "summary_id": result["summary"]["summary_id"],
        "eval": serialize(result["eval"]),
    }


@router.get("/runs/{run_id}/approvals")
async def get_approvals(
    request: Request,
    run_id: str,
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
):
    run = _authorized_run(request, runtime, run_id)
    return {"approvals": serialize(run.approvals)}


@router.post("/runs/{run_id}/approvals/{approval_id}", status_code=202)
async def resolve_approval(
    request: Request,
    run_id: str,
    approval_id: str,
    body: ApprovalRequest,
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
    worker: AsyncioWorker = Depends(deps.get_daemon_worker),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    try:
        _authorized_run(request, runtime, run_id)
        ensure_approval_authority(request, governance, approval_id)
        run = await worker.resolve_approval(run_id, approval_id, body.approved)
        record_approval_actor(request, governance, approval_id, run_id, body.approved)
        return serialize(run)
    except KeyError as exc:
        raise HTTPException(404, str(exc))


def _authorized_run(request: Request, runtime: IResearchAgentRuntime, run_id: str) -> AgentRun:
    run = runtime.get_run(run_id)
    if run is None:
        raise HTTPException(404, "run not found")
    if is_enterprise_request(request):
        if _run_tenant_id(run) != enterprise_context(request).tenant_id:
            raise HTTPException(404, "run not found")
    return run


def _max_event_sequence_after(runtime: IResearchAgentRuntime, run_id: str, after_sequence: int) -> int:
    return max((event.sequence for event in runtime.list_events(run_id) if event.sequence > after_sequence), default=after_sequence)


def _build_authorized_summary(
    request: Request,
    run: AgentRun,
    use_case: BuildRunSummary,
    governance: IEnterpriseGovernanceRepository,
) -> dict:
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


def _run_tenant_id(run: AgentRun) -> str | None:
    if run.identity_snapshot is not None:
        return run.identity_snapshot.tenant_id
    return None

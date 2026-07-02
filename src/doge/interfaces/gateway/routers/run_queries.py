"""v1 run query routes (read paths)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from doge.application.use_cases.run_summary import BuildRunSummary
from doge.core.ports.agent_runtime import IResearchAgentRuntime
from doge.core.ports.enterprise_governance import IEnterpriseGovernanceRepository
from doge.interfaces.api import deps
from doge.interfaces.api.handlers import (
    GetRunHandler,
    GetRunSummaryHandler,
    ListArtifactsHandler,
    ListEventsHandler,
    RunNotFound,
)
from doge.interfaces.gateway.routers._common import serialize
from doge.interfaces.gateway.routers._response_models import (
    RunCitationsEnvelopeResponse,
    RunClaimsEnvelopeResponse,
    RunEvalEnvelopeResponse,
    RunSummaryEnvelopeResponse,
)
from doge.interfaces.gateway.routers._runs_common import (
    request_run_access,
    require_run_summary_api,
)

router = APIRouter(dependencies=[Depends(deps.require_api_token)])


@router.get("/runs/{run_id}")
async def get_run(
    request: Request,
    run_id: str,
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
):
    try:
        run = GetRunHandler(runtime=runtime).handle(run_id=run_id, access=request_run_access(request))
    except RunNotFound:
        raise HTTPException(404, "run not found")
    return serialize(run)


@router.get("/runs/{run_id}/events")
async def get_events(
    request: Request,
    run_id: str,
    after_sequence: int = 0,
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
):
    try:
        events = ListEventsHandler(runtime=runtime).handle(
            run_id=run_id,
            access=request_run_access(request),
            after_sequence=after_sequence,
        )
    except RunNotFound:
        raise HTTPException(404, "run not found")
    return {"events": serialize(events)}


@router.get("/runs/{run_id}/artifacts")
async def get_artifacts(
    request: Request,
    run_id: str,
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
):
    try:
        artifacts = ListArtifactsHandler(runtime=runtime).handle(
            run_id=run_id,
            access=request_run_access(request),
        )
    except RunNotFound:
        raise HTTPException(404, "run not found")
    return {"artifacts": serialize(artifacts)}


@router.get(
    "/runs/{run_id}/summary",
    response_model=RunSummaryEnvelopeResponse,
    dependencies=[Depends(require_run_summary_api)],
)
async def get_run_summary(
    request: Request,
    run_id: str,
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
    use_case: BuildRunSummary = Depends(deps.get_run_summary_use_case),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    try:
        access = request_run_access(request)
        run = GetRunHandler(runtime=runtime).handle(run_id=run_id, access=access)
    except RunNotFound:
        raise HTTPException(404, "run not found")
    result = GetRunSummaryHandler(use_case=use_case, governance=governance).handle(
        run=run,
        access=access,
        audit_event_type="run_summary_read",
    )
    return {"summary": serialize(result["summary"]), "relations": serialize(result["relations"])}


@router.get(
    "/runs/{run_id}/claims",
    response_model=RunClaimsEnvelopeResponse,
    dependencies=[Depends(require_run_summary_api)],
)
async def get_run_claims(
    request: Request,
    run_id: str,
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
    use_case: BuildRunSummary = Depends(deps.get_run_summary_use_case),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    try:
        access = request_run_access(request)
        run = GetRunHandler(runtime=runtime).handle(run_id=run_id, access=access)
    except RunNotFound:
        raise HTTPException(404, "run not found")
    result = GetRunSummaryHandler(use_case=use_case, governance=governance).handle(
        run=run,
        access=access,
        audit_event_type="run_claims_read",
    )
    return {
        "summary_id": result["summary"]["summary_id"],
        "claims": serialize(result["claims"]),
    }


@router.get(
    "/runs/{run_id}/citations",
    response_model=RunCitationsEnvelopeResponse,
    dependencies=[Depends(require_run_summary_api)],
)
async def get_run_citations(
    request: Request,
    run_id: str,
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
    use_case: BuildRunSummary = Depends(deps.get_run_summary_use_case),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    try:
        access = request_run_access(request)
        run = GetRunHandler(runtime=runtime).handle(run_id=run_id, access=access)
    except RunNotFound:
        raise HTTPException(404, "run not found")
    result = GetRunSummaryHandler(use_case=use_case, governance=governance).handle(
        run=run,
        access=access,
        audit_event_type="run_citations_read",
    )
    return {
        "summary_id": result["summary"]["summary_id"],
        "citations": serialize(result["citations"]),
    }


@router.get(
    "/runs/{run_id}/eval",
    response_model=RunEvalEnvelopeResponse,
    dependencies=[Depends(require_run_summary_api)],
)
async def get_run_eval(
    request: Request,
    run_id: str,
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
    use_case: BuildRunSummary = Depends(deps.get_run_summary_use_case),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    try:
        access = request_run_access(request)
        run = GetRunHandler(runtime=runtime).handle(run_id=run_id, access=access)
    except RunNotFound:
        raise HTTPException(404, "run not found")
    result = GetRunSummaryHandler(use_case=use_case, governance=governance).handle(
        run=run,
        access=access,
        audit_event_type="run_eval_read",
    )
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
    try:
        run = GetRunHandler(runtime=runtime).handle(run_id=run_id, access=request_run_access(request))
    except RunNotFound:
        raise HTTPException(404, "run not found")
    return {"approvals": serialize(run.approvals)}

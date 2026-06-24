"""v1 run query routes (read paths)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from doge.application.use_cases.run_summary import BuildRunSummary
from doge.core.ports.agent_runtime import IResearchAgentRuntime
from doge.core.ports.enterprise_governance import IEnterpriseGovernanceRepository
from doge.interfaces.api import deps
from doge.interfaces.api.enterprise_access import append_audit
from doge.interfaces.api.routers.v1._common import serialize
from doge.interfaces.api.routers.v1._runs_common import (
    authorized_run,
    build_authorized_summary,
    request_scope,
    require_run_summary_api,
)

router = APIRouter(dependencies=[Depends(deps.require_api_token)])


@router.get("/runs/{run_id}")
async def get_run(
    request: Request,
    run_id: str,
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
):
    return serialize(authorized_run(request, runtime, run_id))


@router.get("/runs/{run_id}/events")
async def get_events(
    request: Request,
    run_id: str,
    after_sequence: int = 0,
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
):
    scope = request_scope(request)
    authorized_run(request, runtime, run_id)
    events = [
        event for event in runtime.list_events(scope, run_id)
        if event.sequence > after_sequence
    ]
    return {"events": serialize(events)}


@router.get("/runs/{run_id}/artifacts")
async def get_artifacts(
    request: Request,
    run_id: str,
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
):
    scope = request_scope(request)
    authorized_run(request, runtime, run_id)
    return {"artifacts": serialize(runtime.list_artifacts(scope, run_id))}


@router.get("/runs/{run_id}/summary", dependencies=[Depends(require_run_summary_api)])
async def get_run_summary(
    request: Request,
    run_id: str,
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
    use_case: BuildRunSummary = Depends(deps.get_run_summary_use_case),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    run = authorized_run(request, runtime, run_id)
    result = build_authorized_summary(request, run, use_case, governance)
    append_audit(request, governance, "run_summary_read", "run", run_id)
    return {"summary": serialize(result["summary"])}


@router.get("/runs/{run_id}/claims", dependencies=[Depends(require_run_summary_api)])
async def get_run_claims(
    request: Request,
    run_id: str,
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
    use_case: BuildRunSummary = Depends(deps.get_run_summary_use_case),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    run = authorized_run(request, runtime, run_id)
    result = build_authorized_summary(request, run, use_case, governance)
    append_audit(request, governance, "run_claims_read", "run", run_id)
    return {
        "summary_id": result["summary"]["summary_id"],
        "claims": serialize(result["claims"]),
    }


@router.get("/runs/{run_id}/citations", dependencies=[Depends(require_run_summary_api)])
async def get_run_citations(
    request: Request,
    run_id: str,
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
    use_case: BuildRunSummary = Depends(deps.get_run_summary_use_case),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    run = authorized_run(request, runtime, run_id)
    result = build_authorized_summary(request, run, use_case, governance)
    append_audit(request, governance, "run_citations_read", "run", run_id)
    return {
        "summary_id": result["summary"]["summary_id"],
        "citations": serialize(result["citations"]),
    }


@router.get("/runs/{run_id}/eval", dependencies=[Depends(require_run_summary_api)])
async def get_run_eval(
    request: Request,
    run_id: str,
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
    use_case: BuildRunSummary = Depends(deps.get_run_summary_use_case),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    run = authorized_run(request, runtime, run_id)
    result = build_authorized_summary(request, run, use_case, governance)
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
    run = authorized_run(request, runtime, run_id)
    return {"approvals": serialize(run.approvals)}

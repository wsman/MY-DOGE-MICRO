"""v1 run action routes (cancel, resolve approval)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from doge.core.ports.agent_runtime import IResearchAgentRuntime
from doge.core.ports.enterprise_governance import IEnterpriseGovernanceRepository
from doge.interfaces.api import deps
from doge.interfaces.api.handlers import CancelRunHandler, ResolveApprovalHandler
from doge.interfaces.api.handlers.queries import RunNotFound
from doge.interfaces.api.routers.v1._common import serialize
from doge.interfaces.api.routers.v1._runs_common import request_run_access

router = APIRouter(dependencies=[Depends(deps.require_api_token)])


class ApprovalRequest(BaseModel):
    approved: bool = True


@router.post("/runs/{run_id}/cancel", status_code=202)
async def cancel_run(
    request: Request,
    run_id: str,
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
    worker=Depends(deps.get_daemon_worker),
):
    try:
        result = await CancelRunHandler(worker=worker, runtime=runtime).handle(
            run_id=run_id,
            access=request_run_access(request),
        )
        return serialize(result)
    except (KeyError, RunNotFound):
        raise HTTPException(404, "run not found")


@router.post("/runs/{run_id}/approvals/{approval_id}", status_code=202)
async def resolve_approval(
    request: Request,
    run_id: str,
    approval_id: str,
    body: ApprovalRequest,
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
    worker=Depends(deps.get_daemon_worker),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    try:
        run = await ResolveApprovalHandler(
            worker=worker,
            runtime=runtime,
            governance=governance,
        ).handle(
            run_id=run_id,
            approval_id=approval_id,
            approved=body.approved,
            access=request_run_access(request),
        )
        return serialize(run)
    except PermissionError as exc:
        raise HTTPException(403, str(exc))
    except (KeyError, RunNotFound) as exc:
        raise HTTPException(404, str(exc))

"""v1 run action routes (cancel, resolve approval)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from doge.application.agent.worker import AsyncioWorker
from doge.core.ports.agent_runtime import IResearchAgentRuntime
from doge.core.ports.enterprise_governance import IEnterpriseGovernanceRepository
from doge.interfaces.api import deps
from doge.interfaces.api.enterprise_access import (
    ensure_approval_authority,
    record_approval_actor,
)
from doge.interfaces.api.routers.v1._common import serialize
from doge.interfaces.api.routers.v1._runs_common import (
    authorized_run,
    request_scope,
)

router = APIRouter(dependencies=[Depends(deps.require_api_token)])


class ApprovalRequest(BaseModel):
    approved: bool = True


@router.post("/runs/{run_id}/cancel", status_code=202)
async def cancel_run(
    request: Request,
    run_id: str,
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
    worker: AsyncioWorker = Depends(deps.get_daemon_worker),
):
    scope = request_scope(request)
    authorized_run(request, runtime, run_id)
    try:
        return serialize(await worker.cancel_run(run_id, scope=scope))
    except KeyError:
        raise HTTPException(404, "run not found")


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
        scope = request_scope(request)
        authorized_run(request, runtime, run_id)
        ensure_approval_authority(request, governance, approval_id)
        run = await worker.resolve_approval(run_id, approval_id, body.approved, scope=scope)
        record_approval_actor(request, governance, approval_id, run_id, body.approved)
        return serialize(run)
    except KeyError as exc:
        raise HTTPException(404, str(exc))

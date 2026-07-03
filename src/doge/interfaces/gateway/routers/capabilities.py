"""v1 capability-registry routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from doge.platform.workspace import BuildCapabilityRegistry
from doge.core.ports.enterprise_governance import IEnterpriseGovernanceRepository
from doge.interfaces.api import deps
from doge.interfaces.api.enterprise_access import (
    append_audit,
    enterprise_context,
    is_enterprise_request,
)
from doge.interfaces.gateway.routers._common import serialize
from doge.interfaces.gateway.routers._response_models import CapabilitySnapshotResponse
from doge.interfaces.gateway.routers._platform_common import require_capability_registry

router = APIRouter(dependencies=[Depends(deps.require_api_token)])


@router.get(
    "/capabilities",
    response_model=CapabilitySnapshotResponse,
    dependencies=[Depends(require_capability_registry)],
)
async def get_capabilities(
    request: Request,
    use_case: BuildCapabilityRegistry = Depends(deps.get_capability_registry_use_case),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    result = use_case.build(context=enterprise_context(request) if is_enterprise_request(request) else None)
    append_audit(
        request,
        governance,
        "capability_list",
        "capability",
        "*",
        metadata={"count": len(result["capabilities"]), "snapshot_id": result["snapshot_id"]},
    )
    return serialize(result)

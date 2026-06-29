"""v1 enterprise governance administration routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from doge.core.ports.enterprise_governance import EnterpriseAclGrant, IEnterpriseGovernanceRepository
from doge.interfaces.api import deps
from doge.interfaces.api.enterprise_access import (
    append_audit,
    enterprise_context,
    ensure_acl_admin,
)
from doge.interfaces.gateway.routers._common import serialize

router = APIRouter(dependencies=[Depends(deps.require_api_token)])


class AclGrantRequest(BaseModel):
    subject_hash: str
    resource_type: str
    resource_id: str
    permission: str
    provenance: str = "api"


@router.get("/enterprise/acl/grants")
async def list_acl_grants(
    request: Request,
    subject_hash: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    permission: str | None = None,
    limit: int = Query(default=200, ge=1, le=1000),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    ensure_acl_admin(request)
    context = enterprise_context(request)
    grants = governance.list_acl_grants(
        tenant_id=context.tenant_id,
        subject_hash=subject_hash,
        resource_type=resource_type,
        resource_id=resource_id,
        permission=permission,
    )[-limit:]
    append_audit(
        request,
        governance,
        "acl_list",
        "acl",
        "*",
        metadata={
            "count": len(grants),
            "subject_hash": subject_hash,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "permission": permission,
        },
    )
    return {"grants": serialize(grants)}


@router.post("/enterprise/acl/grants", status_code=201)
async def grant_acl(
    request: Request,
    body: AclGrantRequest,
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    ensure_acl_admin(request)
    context = enterprise_context(request)
    grant = EnterpriseAclGrant(
        tenant_id=context.tenant_id,
        subject_hash=body.subject_hash,
        resource_type=body.resource_type,
        resource_id=body.resource_id,
        permission=body.permission,
        provenance=body.provenance,
    )
    governance.grant(grant)
    append_audit(
        request,
        governance,
        "acl_grant",
        "acl",
        f"{body.resource_type}:{body.resource_id}:{body.permission}",
        metadata={
            "subject_hash": body.subject_hash,
            "provenance": body.provenance,
        },
    )
    return serialize(grant)


@router.delete("/enterprise/acl/grants")
async def revoke_acl(
    request: Request,
    subject_hash: str,
    resource_type: str,
    resource_id: str,
    permission: str,
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    ensure_acl_admin(request)
    context = enterprise_context(request)
    deleted = governance.revoke_grant(
        context.tenant_id,
        subject_hash,
        resource_type,
        resource_id,
        permission,
    )
    append_audit(
        request,
        governance,
        "acl_revoke",
        "acl",
        f"{resource_type}:{resource_id}:{permission}",
        metadata={
            "subject_hash": subject_hash,
            "deleted": deleted,
        },
    )
    return {"deleted": deleted}

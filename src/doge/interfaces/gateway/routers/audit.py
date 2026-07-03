"""v1 enterprise audit routes."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from doge.platform.governance import build_audit_export_manifest
from doge.config import get_settings
from doge.core.security import redact_secrets
from doge.core.ports.enterprise_governance import IEnterpriseGovernanceRepository
from doge.interfaces.api import deps
from doge.interfaces.api.enterprise_access import (
    append_audit,
    enterprise_context,
    ensure_acl_admin,
    is_enterprise_request,
)
from doge.interfaces.gateway.routers._common import serialize

router = APIRouter(dependencies=[Depends(deps.require_api_token)])


@router.get("/audit/events")
async def list_audit_events(
    request: Request,
    tenant_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    """List audit events visible to the caller's trusted tenant context."""

    effective_tenant_id = enterprise_context(request).tenant_id if is_enterprise_request(request) else tenant_id
    events = governance.list_audit_events(effective_tenant_id)
    return {"events": serialize(events[-limit:])}


@router.get("/audit/events/export")
async def export_audit_events(
    request: Request,
    format: str = Query(default="jsonl", pattern="^jsonl$"),
    limit: int = Query(default=1000, ge=1, le=10000),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    """Export tenant-scoped audit events as newline-delimited JSON for SIEM ingestion."""

    ensure_acl_admin(request)
    context = enterprise_context(request)
    events = governance.list_audit_events(context.tenant_id)[-limit:]
    lines = [
        json.dumps(redact_secrets(serialize(event)), ensure_ascii=False, sort_keys=True)
        for event in events
    ]
    append_audit(
        request,
        governance,
        "audit_export",
        "audit",
        context.tenant_id,
        metadata={"count": len(events), "format": format},
    )
    content = "\n".join(lines)
    if content:
        content += "\n"
    manifest_headers = build_audit_export_manifest(content, event_count=len(events)).to_headers()
    manifest_headers["Content-Disposition"] = f'attachment; filename="doge-audit-{context.tenant_id}.jsonl"'
    return Response(
        content=content,
        media_type="application/x-ndjson",
        headers=manifest_headers,
    )


@router.post("/audit/events/retention")
async def purge_audit_events(
    request: Request,
    retention_days: int | None = Query(default=None, ge=1, le=3650),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    """Purge expired audit events for the caller's tenant."""

    ensure_acl_admin(request)
    context = enterprise_context(request)
    configured_days = get_settings().audit.retention_days
    days = retention_days if retention_days is not None else max(1, configured_days)
    before_created_at = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    deleted = governance.purge_audit_events(context.tenant_id, before_created_at)
    append_audit(
        request,
        governance,
        "audit_retention_purge",
        "audit",
        context.tenant_id,
        metadata={
            "retention_days": days,
            "before_created_at": before_created_at,
            "deleted": deleted,
        },
    )
    return {"deleted": deleted, "retention_days": days, "before_created_at": before_created_at}

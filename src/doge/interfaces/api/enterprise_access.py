"""Helpers for API routes that need enterprise ACL/audit decisions."""

from __future__ import annotations

from fastapi import HTTPException, Request

from doge.core.domain.enterprise_context import (
    IDENTITY_SNAPSHOT_KEYS,
    EnterpriseContext,
    IdentitySnapshot,
)
from doge.core.ports.enterprise_governance import (
    ApprovalActorDecision,
    EnterpriseAclGrant,
    EnterpriseAuditEvent,
    IEnterpriseGovernanceRepository,
)


def enterprise_context(request: Request) -> EnterpriseContext:
    return getattr(request.state, "enterprise_context", EnterpriseContext())


def is_enterprise_request(request: Request) -> bool:
    return bool(getattr(request.state, "authenticated_principal", None))


def request_id(request: Request) -> str | None:
    return request.headers.get("x-request-id") or request.headers.get("x-correlation-id")


def grant_creator_access(
    request: Request,
    governance: IEnterpriseGovernanceRepository,
    resource_type: str,
    resource_id: str,
    *,
    provenance: str,
) -> None:
    if not is_enterprise_request(request):
        return
    context = enterprise_context(request)
    for permission in ("read", "write", "execute"):
        if resource_type != "tool" and permission == "execute":
            continue
        governance.grant(
            EnterpriseAclGrant(
                tenant_id=context.tenant_id,
                subject_hash=context.user_hash,
                resource_type=resource_type,
                resource_id=resource_id,
                permission=permission,
                provenance=provenance,
            )
        )


def ensure_resource_access(
    request: Request,
    governance: IEnterpriseGovernanceRepository,
    resource_type: str,
    resource_id: str,
    permission: str,
) -> None:
    context = enterprise_context(request)
    if not is_enterprise_request(request):
        _ensure_local_context_access(context, resource_type, resource_id)
        return
    if governance.is_allowed(context, resource_type, resource_id, permission):
        return
    if _inline_context_allows(context, resource_type, resource_id):
        return
    raise HTTPException(403, f"{resource_type} access denied")


def filter_accessible_resource_ids(
    request: Request,
    governance: IEnterpriseGovernanceRepository,
    resource_type: str,
    resource_ids: list[str],
    permission: str,
) -> set[str]:
    context = enterprise_context(request)
    if not is_enterprise_request(request):
        return {
            resource_id
            for resource_id in resource_ids
            if _local_context_allows(context, resource_type, resource_id)
        }
    allowed = governance.list_allowed_resource_ids(context, resource_type, permission)
    if "*" in allowed:
        return set(resource_ids)
    inline = {
        resource_id
        for resource_id in resource_ids
        if _inline_context_allows(context, resource_type, resource_id)
    }
    return (allowed & set(resource_ids)) | inline


def redact_run_summary_for_request(
    request: Request,
    governance: IEnterpriseGovernanceRepository,
    result: dict,
) -> dict:
    """Apply document ACL citation redaction for a run-summary payload."""
    if not is_enterprise_request(request):
        return result
    from doge.platform.evidence import redact_inaccessible_citations

    document_ids = sorted(
        {
            citation["document_id"]
            for citation in result.get("citations", [])
            if citation.get("document_id")
        }
    )
    allowed = filter_accessible_resource_ids(request, governance, "document", document_ids, "read")
    return redact_inaccessible_citations(result, allowed)


def append_audit(
    request: Request,
    governance: IEnterpriseGovernanceRepository,
    event_type: str,
    resource_type: str,
    resource_id: str,
    *,
    metadata: dict | None = None,
) -> None:
    if not is_enterprise_request(request):
        return
    context = enterprise_context(request)
    governance.append_audit_event(
        EnterpriseAuditEvent(
            tenant_id=context.tenant_id,
            actor_hash=context.user_hash,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            request_id=request_id(request),
            metadata=metadata or {},
        )
    )


def record_approval_actor(
    request: Request,
    governance: IEnterpriseGovernanceRepository,
    approval_id: str,
    run_id: str,
    approved: bool,
) -> None:
    if not is_enterprise_request(request):
        return
    context = enterprise_context(request)
    governance.record_approval_decision(
        ApprovalActorDecision(
            approval_id=approval_id,
            run_id=run_id,
            tenant_id=context.tenant_id,
            actor_hash=context.user_hash,
            request_id=request_id(request),
            authority_source="enterprise_context",
            decision="approved" if approved else "rejected",
            metadata={"approval_authority": sorted(context.approval_authority)},
        )
    )
    append_audit(
        request,
        governance,
        "approval_decision",
        "approval",
        approval_id,
        metadata={"run_id": run_id, "approved": approved},
    )


def ensure_acl_admin(request: Request) -> None:
    if not is_enterprise_request(request):
        raise HTTPException(403, "enterprise ACL administration requires authenticated enterprise context")
    context = enterprise_context(request)
    principal = getattr(request.state, "authenticated_principal", None)
    roles = set(getattr(principal, "roles", ()) or ())
    roles.add(context.role)
    if roles & {"tenant_admin", "security_admin", "compliance_admin"}:
        return
    if "enterprise_acl_admin" in context.tool_entitlement:
        return
    raise HTTPException(403, "ACL administration access denied")


def ensure_approval_authority(
    request: Request,
    governance: IEnterpriseGovernanceRepository,
    approval_id: str,
) -> None:
    if not is_enterprise_request(request):
        return
    context = enterprise_context(request)
    if governance.is_allowed(context, "approval", approval_id, "approve"):
        return
    if "*" in context.approval_authority or approval_id in context.approval_authority:
        return
    raise HTTPException(403, "approval access denied")


def tool_allowed(
    request: Request,
    governance: IEnterpriseGovernanceRepository,
    tool_name: str,
    category: str,
) -> bool:
    context = enterprise_context(request)
    if not is_enterprise_request(request):
        return True
    if governance.is_allowed(context, "tool", tool_name, "execute"):
        return True
    return "*" in context.tool_entitlement or tool_name in context.tool_entitlement or category in context.tool_entitlement


def trusted_model_policy(
    request: Request,
    governance: IEnterpriseGovernanceRepository,
    base_policy: dict,
) -> dict:
    """Return model execution policy with any untrusted identity fields removed."""

    return {
        key: value
        for key, value in dict(base_policy).items()
        if key not in IDENTITY_SNAPSHOT_KEYS
    }


def trusted_identity_snapshot(
    request: Request,
    governance: IEnterpriseGovernanceRepository,
) -> IdentitySnapshot | None:
    """Capture trusted enterprise identity/ACL context for a run."""

    if not is_enterprise_request(request):
        return None
    context = enterprise_context(request)
    return IdentitySnapshot(
        tenant_id=context.tenant_id,
        user_hash=context.user_hash,
        role=context.role,
        data_classification=context.data_classification,
        project_id=context.project_id,
        request_id=request_id(request),
        document_acl=tuple(sorted(
            _merge_inline_and_persistent(context.document_acl, governance, context, "document", "read")
        )),
        portfolio_permission=tuple(sorted(
            _merge_inline_and_persistent(context.portfolio_permission, governance, context, "portfolio", "read")
        )),
        tool_entitlement=tuple(sorted(
            _merge_inline_and_persistent(context.tool_entitlement, governance, context, "tool", "execute")
        )),
        approval_authority=tuple(sorted(
            _merge_inline_and_persistent(context.approval_authority, governance, context, "approval", "approve")
        )),
    )


def _merge_inline_and_persistent(
    inline: frozenset[str],
    governance: IEnterpriseGovernanceRepository,
    context: EnterpriseContext,
    resource_type: str,
    permission: str,
) -> set[str]:
    return set(inline) | governance.list_allowed_resource_ids(context, resource_type, permission)


def _ensure_local_context_access(context: EnterpriseContext, resource_type: str, resource_id: str) -> None:
    if _local_context_allows(context, resource_type, resource_id):
        return
    raise HTTPException(403, f"{resource_type} access denied")


def _local_context_allows(context: EnterpriseContext, resource_type: str, resource_id: str) -> bool:
    if resource_type == "document":
        return context.can_access_document(resource_id)
    if resource_type == "portfolio":
        return context.can_access_portfolio(resource_id)
    return True


def _inline_context_allows(context: EnterpriseContext, resource_type: str, resource_id: str) -> bool:
    if resource_type == "document":
        return resource_id in context.document_acl
    if resource_type == "portfolio":
        return resource_id in context.portfolio_permission
    if resource_type == "tool":
        return resource_id in context.tool_entitlement
    if resource_type == "approval":
        return resource_id in context.approval_authority
    return False

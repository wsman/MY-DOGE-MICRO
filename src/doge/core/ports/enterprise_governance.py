"""Ports and records for enterprise ACL and audit governance."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import uuid4

from doge.core.domain.agent_models import utc_now
from doge.core.domain.enterprise_context import EnterpriseContext


@dataclass(frozen=True)
class EnterpriseAclGrant:
    tenant_id: str
    subject_hash: str
    resource_type: str
    resource_id: str
    permission: str
    provenance: str = "manual"
    created_at: str = field(default_factory=utc_now)


@dataclass(frozen=True)
class EnterpriseAuditEvent:
    event_type: str
    tenant_id: str
    actor_hash: str
    resource_type: str
    resource_id: str
    request_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    audit_id: str = field(default_factory=lambda: f"audit-{uuid4().hex[:12]}")
    created_at: str = field(default_factory=utc_now)


@dataclass(frozen=True)
class ApprovalActorDecision:
    approval_id: str
    run_id: str
    tenant_id: str
    actor_hash: str
    decision: str
    request_id: str | None = None
    authority_source: str = "enterprise_context"
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)


class IEnterpriseGovernanceRepository(Protocol):
    def grant(self, grant: EnterpriseAclGrant) -> None:
        ...

    def revoke_grant(
        self,
        tenant_id: str,
        subject_hash: str,
        resource_type: str,
        resource_id: str,
        permission: str,
    ) -> bool:
        ...

    def list_acl_grants(
        self,
        tenant_id: str | None = None,
        subject_hash: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        permission: str | None = None,
    ) -> list[EnterpriseAclGrant]:
        ...

    def is_allowed(
        self,
        context: EnterpriseContext,
        resource_type: str,
        resource_id: str,
        permission: str,
    ) -> bool:
        ...

    def list_allowed_resource_ids(
        self,
        context: EnterpriseContext,
        resource_type: str,
        permission: str,
    ) -> set[str]:
        ...

    def append_audit_event(self, event: EnterpriseAuditEvent) -> EnterpriseAuditEvent:
        ...

    def list_audit_events(self, tenant_id: str | None = None) -> list[EnterpriseAuditEvent]:
        ...

    def purge_audit_events(self, tenant_id: str, before_created_at: str) -> int:
        ...

    def record_approval_decision(self, decision: ApprovalActorDecision) -> None:
        ...

    def list_approval_decisions(self, approval_id: str | None = None) -> list[ApprovalActorDecision]:
        ...

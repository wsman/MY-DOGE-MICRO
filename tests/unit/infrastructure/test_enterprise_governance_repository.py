from doge.core.domain.enterprise_context import EnterpriseContext
from doge.core.ports.enterprise_governance import (
    ApprovalActorDecision,
    EnterpriseAclGrant,
    EnterpriseAuditEvent,
)
from doge.infrastructure.database.enterprise_governance import SQLiteEnterpriseGovernanceRepository


def test_enterprise_acl_grants_are_tenant_and_subject_scoped(tmp_path):
    repository = SQLiteEnterpriseGovernanceRepository(tmp_path / "agent.db")
    tenant_a = EnterpriseContext(tenant_id="tenant-a", user_hash="user-a")
    tenant_b = EnterpriseContext(tenant_id="tenant-b", user_hash="user-a")
    other_user = EnterpriseContext(tenant_id="tenant-a", user_hash="user-b")

    repository.grant(
        EnterpriseAclGrant(
            tenant_id="tenant-a",
            subject_hash="user-a",
            resource_type="document",
            resource_id="doc-1",
            permission="read",
            provenance="test",
        )
    )

    assert repository.is_allowed(tenant_a, "document", "doc-1", "read") is True
    assert repository.is_allowed(tenant_a, "document", "doc-1", "write") is False
    assert repository.is_allowed(tenant_b, "document", "doc-1", "read") is False
    assert repository.is_allowed(other_user, "document", "doc-1", "read") is False
    assert repository.list_allowed_resource_ids(tenant_a, "document", "read") == {"doc-1"}


def test_enterprise_acl_supports_wildcards(tmp_path):
    repository = SQLiteEnterpriseGovernanceRepository(tmp_path / "agent.db")
    context = EnterpriseContext(tenant_id="tenant-a", user_hash="user-a")

    repository.grant(
        EnterpriseAclGrant(
            tenant_id="tenant-a",
            subject_hash="user-a",
            resource_type="tool",
            resource_id="*",
            permission="execute",
            provenance="test",
        )
    )

    assert repository.is_allowed(context, "tool", "query_stock", "execute") is True
    assert repository.list_allowed_resource_ids(context, "tool", "execute") == {"*"}


def test_enterprise_acl_grants_can_be_listed_and_revoked(tmp_path):
    repository = SQLiteEnterpriseGovernanceRepository(tmp_path / "agent.db")
    grant = EnterpriseAclGrant(
        tenant_id="tenant-a",
        subject_hash="user-a",
        resource_type="tool",
        resource_id="query_stock",
        permission="execute",
        provenance="test",
    )
    repository.grant(grant)
    repository.grant(
        EnterpriseAclGrant(
            tenant_id="tenant-b",
            subject_hash="user-a",
            resource_type="tool",
            resource_id="query_stock",
            permission="execute",
            provenance="test",
        )
    )

    tenant_a_grants = repository.list_acl_grants(tenant_id="tenant-a")
    deleted = repository.revoke_grant("tenant-a", "user-a", "tool", "query_stock", "execute")

    assert tenant_a_grants == [grant]
    assert deleted is True
    assert repository.list_acl_grants(tenant_id="tenant-a") == []
    assert len(repository.list_acl_grants(tenant_id="tenant-b")) == 1
    assert repository.revoke_grant("tenant-a", "user-a", "tool", "query_stock", "execute") is False


def test_enterprise_audit_and_approval_actor_records_are_append_only(tmp_path):
    repository = SQLiteEnterpriseGovernanceRepository(tmp_path / "agent.db")

    repository.append_audit_event(
        EnterpriseAuditEvent(
            tenant_id="tenant-a",
            actor_hash="user-a",
            event_type="document_read",
            resource_type="document",
            resource_id="doc-1",
            request_id="req-1",
            metadata={"source": "test"},
        )
    )
    repository.record_approval_decision(
        ApprovalActorDecision(
            approval_id="appr-1",
            run_id="run-1",
            tenant_id="tenant-a",
            actor_hash="user-a",
            request_id="req-1",
            authority_source="acl",
            decision="approved",
            metadata={"reason": "ok"},
        )
    )

    audit_events = repository.list_audit_events("tenant-a")
    approval_events = repository.list_approval_decisions("appr-1")

    assert len(audit_events) == 1
    assert audit_events[0].metadata == {"source": "test"}
    assert audit_events[0].request_id == "req-1"
    assert len(approval_events) == 1
    assert approval_events[0].actor_hash == "user-a"
    assert approval_events[0].decision == "approved"
    assert approval_events[0].metadata == {"reason": "ok"}


def test_enterprise_audit_events_can_be_purged_by_tenant_and_cutoff(tmp_path):
    repository = SQLiteEnterpriseGovernanceRepository(tmp_path / "agent.db")
    repository.append_audit_event(
        EnterpriseAuditEvent(
            tenant_id="tenant-a",
            actor_hash="user-a",
            event_type="old_a",
            resource_type="run",
            resource_id="run-old-a",
            created_at="2025-01-01T00:00:00+00:00",
        )
    )
    repository.append_audit_event(
        EnterpriseAuditEvent(
            tenant_id="tenant-a",
            actor_hash="user-a",
            event_type="new_a",
            resource_type="run",
            resource_id="run-new-a",
            created_at="2026-01-01T00:00:00+00:00",
        )
    )
    repository.append_audit_event(
        EnterpriseAuditEvent(
            tenant_id="tenant-b",
            actor_hash="user-b",
            event_type="old_b",
            resource_type="run",
            resource_id="run-old-b",
            created_at="2025-01-01T00:00:00+00:00",
        )
    )

    deleted = repository.purge_audit_events("tenant-a", "2025-06-01T00:00:00+00:00")

    assert deleted == 1
    assert [event.event_type for event in repository.list_audit_events("tenant-a")] == ["new_a"]
    assert [event.event_type for event in repository.list_audit_events("tenant-b")] == ["old_b"]

"""SQLite enterprise ACL and audit repository."""

from __future__ import annotations

import json
from pathlib import Path

from doge.config import get_settings
from doge.core.domain.enterprise_context import EnterpriseContext
from doge.core.ports.enterprise_governance import (
    ApprovalActorDecision,
    EnterpriseAclGrant,
    EnterpriseAuditEvent,
    IEnterpriseGovernanceRepository,
)
from doge.infrastructure.database.agent_repositories import bootstrap_agent_schema
from doge.infrastructure.database.sqlite import SQLiteConnection


class SQLiteEnterpriseGovernanceRepository(IEnterpriseGovernanceRepository):
    def __init__(self, db_path: Path | str | None = None) -> None:
        self._db_path = Path(db_path) if db_path is not None else get_settings().db.agent_db
        bootstrap_agent_schema(self._db_path)
        self._connection = SQLiteConnection(self._db_path, use_row_factory=True)

    def _connect(self):
        return self._connection.connect()

    def grant(self, grant: EnterpriseAclGrant) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO enterprise_acl_grants(
                    tenant_id, subject_hash, resource_type, resource_id,
                    permission, provenance, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    grant.tenant_id,
                    grant.subject_hash,
                    grant.resource_type,
                    grant.resource_id,
                    grant.permission,
                    grant.provenance,
                    grant.created_at,
                ),
            )
            conn.commit()

    def revoke_grant(
        self,
        tenant_id: str,
        subject_hash: str,
        resource_type: str,
        resource_id: str,
        permission: str,
    ) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                DELETE FROM enterprise_acl_grants
                WHERE tenant_id = ?
                  AND subject_hash = ?
                  AND resource_type = ?
                  AND resource_id = ?
                  AND permission = ?
                """,
                (tenant_id, subject_hash, resource_type, resource_id, permission),
            )
            conn.commit()
        return cursor.rowcount > 0

    def list_acl_grants(
        self,
        tenant_id: str | None = None,
        subject_hash: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        permission: str | None = None,
    ) -> list[EnterpriseAclGrant]:
        filters = {
            "tenant_id": tenant_id,
            "subject_hash": subject_hash,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "permission": permission,
        }
        clauses = [f"{column} = ?" for column, value in filters.items() if value is not None]
        params = tuple(value for value in filters.values() if value is not None)
        sql = "SELECT * FROM enterprise_acl_grants"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY created_at ASC, tenant_id ASC, subject_hash ASC, resource_type ASC, resource_id ASC"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_row_to_acl_grant(row) for row in rows]

    def is_allowed(
        self,
        context: EnterpriseContext,
        resource_type: str,
        resource_id: str,
        permission: str,
    ) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT 1
                FROM enterprise_acl_grants
                WHERE tenant_id = ?
                  AND subject_hash = ?
                  AND resource_type = ?
                  AND resource_id IN (?, '*')
                  AND permission IN (?, '*')
                LIMIT 1
                """,
                (context.tenant_id, context.user_hash, resource_type, resource_id, permission),
            ).fetchone()
        return row is not None

    def list_allowed_resource_ids(
        self,
        context: EnterpriseContext,
        resource_type: str,
        permission: str,
    ) -> set[str]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT resource_id
                FROM enterprise_acl_grants
                WHERE tenant_id = ?
                  AND subject_hash = ?
                  AND resource_type = ?
                  AND permission IN (?, '*')
                """,
                (context.tenant_id, context.user_hash, resource_type, permission),
            ).fetchall()
        return {row["resource_id"] for row in rows}

    def append_audit_event(self, event: EnterpriseAuditEvent) -> EnterpriseAuditEvent:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO enterprise_audit_events(
                    audit_id, tenant_id, actor_hash, event_type, resource_type,
                    resource_id, request_id, metadata, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.audit_id,
                    event.tenant_id,
                    event.actor_hash,
                    event.event_type,
                    event.resource_type,
                    event.resource_id,
                    event.request_id,
                    json.dumps(event.metadata, ensure_ascii=False),
                    event.created_at,
                ),
            )
            conn.commit()
        return event

    def list_audit_events(self, tenant_id: str | None = None) -> list[EnterpriseAuditEvent]:
        sql = "SELECT * FROM enterprise_audit_events"
        params: tuple[str, ...] = ()
        if tenant_id is not None:
            sql += " WHERE tenant_id = ?"
            params = (tenant_id,)
        sql += " ORDER BY created_at ASC, audit_id ASC"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_row_to_audit_event(row) for row in rows]

    def purge_audit_events(self, tenant_id: str, before_created_at: str) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                DELETE FROM enterprise_audit_events
                WHERE tenant_id = ?
                  AND created_at < ?
                """,
                (tenant_id, before_created_at),
            )
            conn.commit()
        return cursor.rowcount

    def record_approval_decision(self, decision: ApprovalActorDecision) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO approval_actor_decisions(
                    approval_id, run_id, tenant_id, actor_hash, request_id,
                    authority_source, decision, metadata, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision.approval_id,
                    decision.run_id,
                    decision.tenant_id,
                    decision.actor_hash,
                    decision.request_id,
                    decision.authority_source,
                    decision.decision,
                    json.dumps(decision.metadata, ensure_ascii=False),
                    decision.created_at,
                ),
            )
            conn.commit()

    def list_approval_decisions(self, approval_id: str | None = None) -> list[ApprovalActorDecision]:
        sql = "SELECT * FROM approval_actor_decisions"
        params: tuple[str, ...] = ()
        if approval_id is not None:
            sql += " WHERE approval_id = ?"
            params = (approval_id,)
        sql += " ORDER BY created_at ASC"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_row_to_approval_decision(row) for row in rows]


def _row_to_audit_event(row) -> EnterpriseAuditEvent:
    return EnterpriseAuditEvent(
        audit_id=row["audit_id"],
        tenant_id=row["tenant_id"],
        actor_hash=row["actor_hash"],
        event_type=row["event_type"],
        resource_type=row["resource_type"],
        resource_id=row["resource_id"],
        request_id=row["request_id"],
        metadata=json.loads(row["metadata"] or "{}"),
        created_at=row["created_at"],
    )


def _row_to_acl_grant(row) -> EnterpriseAclGrant:
    return EnterpriseAclGrant(
        tenant_id=row["tenant_id"],
        subject_hash=row["subject_hash"],
        resource_type=row["resource_type"],
        resource_id=row["resource_id"],
        permission=row["permission"],
        provenance=row["provenance"],
        created_at=row["created_at"],
    )


def _row_to_approval_decision(row) -> ApprovalActorDecision:
    return ApprovalActorDecision(
        approval_id=row["approval_id"],
        run_id=row["run_id"],
        tenant_id=row["tenant_id"],
        actor_hash=row["actor_hash"],
        request_id=row["request_id"],
        authority_source=row["authority_source"],
        decision=row["decision"],
        metadata=json.loads(row["metadata"] or "{}"),
        created_at=row["created_at"],
    )

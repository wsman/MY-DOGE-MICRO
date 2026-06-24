"""Tenant normalization and write guards for SQLite repositories."""

from __future__ import annotations

from sqlite3 import Connection


LOCAL_TENANT_ID = "local"


def normalize_tenant_id(tenant_id: str | None) -> str:
    return tenant_id or LOCAL_TENANT_ID


def resolve_tenant_id(record_tenant_id: str | None, requested_tenant_id: str | None = None) -> str:
    if requested_tenant_id is not None and record_tenant_id is not None:
        require_same_tenant(record_tenant_id, requested_tenant_id, resource="write payload")
    return normalize_tenant_id(requested_tenant_id if requested_tenant_id is not None else record_tenant_id)


def require_same_tenant(current_tenant_id: str | None, target_tenant_id: str | None, *, resource: str) -> None:
    current = normalize_tenant_id(current_tenant_id)
    target = normalize_tenant_id(target_tenant_id)
    if current != target:
        raise ValueError(f"tenant mismatch for {resource}: {current} != {target}")


def guard_existing_tenant(
    conn: Connection,
    *,
    table: str,
    key_column: str,
    key_value: str,
    tenant_id: str | None,
) -> None:
    row = conn.execute(f"SELECT tenant_id FROM {table} WHERE {key_column} = ?", (key_value,)).fetchone()
    if row is not None:
        require_same_tenant(row["tenant_id"], tenant_id, resource=f"{table}.{key_column}={key_value}")

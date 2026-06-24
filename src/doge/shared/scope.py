"""Explicit tenant scope primitives shared across bounded contexts."""

from __future__ import annotations

from dataclasses import dataclass


LOCAL_TENANT_ID = "local"


@dataclass(frozen=True)
class TenantScope:
    """Trusted runtime scope for tenant-scoped reads and mutations."""

    tenant_id: str
    subject_hash: str | None = None

    def __post_init__(self) -> None:
        tenant_id = (self.tenant_id or "").strip()
        if not tenant_id:
            raise ValueError("tenant_id is required")
        object.__setattr__(self, "tenant_id", tenant_id)

    @classmethod
    def local(cls) -> "TenantScope":
        return cls(tenant_id=LOCAL_TENANT_ID, subject_hash="local-user")

    @classmethod
    def enterprise(cls, tenant_id: str, subject_hash: str | None = None) -> "TenantScope":
        if not (tenant_id or "").strip():
            raise ValueError("enterprise tenant_id is required")
        return cls(tenant_id=tenant_id, subject_hash=subject_hash)

    @classmethod
    def from_tenant_id(cls, tenant_id: str | None, subject_hash: str | None = None) -> "TenantScope":
        if tenant_id is None:
            return cls.local()
        return cls.enterprise(tenant_id=tenant_id, subject_hash=subject_hash)

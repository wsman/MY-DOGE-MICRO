"""Enterprise request context for tenant, entitlement, and data boundaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class IdentitySnapshot:
    """Serializable trusted identity/ACL context captured for one run."""

    tenant_id: str = "local"
    user_hash: str = "local-user"
    role: str = "analyst"
    document_acl: tuple[str, ...] = ()
    tool_entitlement: tuple[str, ...] = ()
    portfolio_permission: tuple[str, ...] = ()
    approval_authority: tuple[str, ...] = ()
    data_classification: str = "internal"
    project_id: str = "doge-dev"
    request_id: str | None = None

    @classmethod
    def from_mapping(cls, data: "IdentitySnapshot | dict[str, Any] | None") -> "IdentitySnapshot | None":
        if data is None:
            return None
        if isinstance(data, cls):
            return data
        payload = dict(data)
        if not any(key in payload for key in IDENTITY_SNAPSHOT_KEYS):
            return None
        return cls(
            tenant_id=_string_value(payload.get("tenant_id"), "local"),
            user_hash=_string_value(payload.get("user_hash"), "local-user"),
            role=_string_value(payload.get("role"), "analyst"),
            document_acl=tuple(sorted(_string_set(payload.get("document_acl")))),
            tool_entitlement=tuple(sorted(_string_set(payload.get("tool_entitlement")))),
            portfolio_permission=tuple(sorted(_string_set(payload.get("portfolio_permission")))),
            approval_authority=tuple(sorted(_string_set(payload.get("approval_authority")))),
            data_classification=_string_value(payload.get("data_classification"), "internal"),
            project_id=_string_value(payload.get("project_id"), "doge-dev"),
            request_id=_optional_string(payload.get("request_id")),
        )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "user_hash": self.user_hash,
            "role": self.role,
            "document_acl": list(self.document_acl),
            "tool_entitlement": list(self.tool_entitlement),
            "portfolio_permission": list(self.portfolio_permission),
            "approval_authority": list(self.approval_authority),
            "data_classification": self.data_classification,
            "project_id": self.project_id,
            "request_id": self.request_id,
        }
        return {key: value for key, value in data.items() if value is not None}


@dataclass(frozen=True)
class EnterpriseContext:
    tenant_id: str = "local"
    user_hash: str = "local-user"
    role: str = "analyst"
    document_acl: frozenset[str] = field(default_factory=frozenset)
    tool_entitlement: frozenset[str] = field(default_factory=frozenset)
    portfolio_permission: frozenset[str] = field(default_factory=frozenset)
    data_classification: str = "internal"
    approval_authority: frozenset[str] = field(default_factory=frozenset)
    project_id: str = "doge-dev"

    def can_access_document(self, document_id: str) -> bool:
        return not self.document_acl or document_id in self.document_acl

    def can_access_portfolio(self, portfolio_id: str | None) -> bool:
        return portfolio_id is None or not self.portfolio_permission or portfolio_id in self.portfolio_permission

    def to_identity_snapshot(self, *, request_id: str | None = None) -> IdentitySnapshot:
        return IdentitySnapshot(
            tenant_id=self.tenant_id,
            user_hash=self.user_hash,
            role=self.role,
            document_acl=tuple(sorted(self.document_acl)),
            tool_entitlement=tuple(sorted(self.tool_entitlement)),
            portfolio_permission=tuple(sorted(self.portfolio_permission)),
            approval_authority=tuple(sorted(self.approval_authority)),
            data_classification=self.data_classification,
            project_id=self.project_id,
            request_id=request_id,
        )

    @classmethod
    def from_identity_snapshot(cls, snapshot: IdentitySnapshot | dict[str, Any] | None) -> "EnterpriseContext":
        normalized = IdentitySnapshot.from_mapping(snapshot)
        if normalized is None:
            return cls()
        return cls(
            tenant_id=normalized.tenant_id,
            user_hash=normalized.user_hash,
            role=normalized.role,
            document_acl=frozenset(normalized.document_acl),
            tool_entitlement=frozenset(normalized.tool_entitlement),
            portfolio_permission=frozenset(normalized.portfolio_permission),
            data_classification=normalized.data_classification,
            approval_authority=frozenset(normalized.approval_authority),
            project_id=normalized.project_id,
        )


@dataclass(frozen=True)
class EnterpriseCallContext:
    """Provider-neutral metadata for one enterprise model call."""

    tenant_id: str
    user_hash: str
    session_id: str
    task_type: str
    response_schema: dict[str, Any] | None = None


IDENTITY_SNAPSHOT_KEYS = frozenset({
    "tenant_id",
    "user_hash",
    "role",
    "document_acl",
    "tool_entitlement",
    "portfolio_permission",
    "approval_authority",
    "data_classification",
    "project_id",
    "request_id",
})


def _string_set(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        return {item.strip() for item in value.split(",") if item.strip()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return {str(item) for item in value if item is not None and str(item) != ""}
    return {str(value)}


def _string_value(value: Any, default: str) -> str:
    if value is None or value == "":
        return default
    return str(value)


def _optional_string(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)

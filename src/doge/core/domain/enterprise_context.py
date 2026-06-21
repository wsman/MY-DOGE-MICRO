"""Enterprise request context for tenant, entitlement, and data boundaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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


@dataclass(frozen=True)
class EnterpriseCallContext:
    """Provider-neutral metadata for one enterprise model call."""

    tenant_id: str
    user_hash: str
    session_id: str
    task_type: str
    response_schema: dict[str, Any] | None = None

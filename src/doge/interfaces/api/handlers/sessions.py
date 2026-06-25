"""Session API handlers without FastAPI dependencies."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from doge.application.use_cases.session_use_cases import CreateSession, ListSessions, ResumeSession
from doge.core.domain.enterprise_context import IDENTITY_SNAPSHOT_KEYS, IdentitySnapshot
from doge.core.ports.enterprise_governance import EnterpriseAuditEvent
from doge.interfaces.api.handlers.queries import RunAccessContext
from doge.shared.scope import TenantScope


class SessionNotFound(KeyError):
    """Raised when a session-scoped command targets a missing session."""


def _scope_for_tenant_id(tenant_id: str | None) -> TenantScope:
    if tenant_id is None:
        return TenantScope.local()
    return TenantScope.enterprise(tenant_id=tenant_id)


@dataclass(frozen=True)
class SubmitSessionTurnCommand:
    session_id: str
    message: str
    market: str = "us"
    language: str = "en"
    document_ids: list[str] = field(default_factory=list)
    portfolio_id: str | None = "portfolio-demo"
    model_policy: dict[str, Any] = field(default_factory=dict)
    identity_snapshot: dict[str, Any] | None = None
    idempotency_key: str | None = None
    tenant_id: str | None = None


class CreateSessionHandler:
    def __init__(self, sessions) -> None:
        self._sessions = sessions

    def handle(self, *, title: str, tenant_id: str | None = None):
        return CreateSession(self._sessions).execute(title=title, scope=_scope_for_tenant_id(tenant_id))


class ListSessionsHandler:
    def __init__(self, sessions) -> None:
        self._sessions = sessions

    def handle(self, *, limit: int = 20, tenant_id: str | None = None):
        return ListSessions(self._sessions).execute(limit=limit, scope=_scope_for_tenant_id(tenant_id))


class GetSessionHandler:
    def __init__(self, sessions) -> None:
        self._sessions = sessions

    def handle(self, *, session_id: str, tenant_id: str | None = None):
        return ResumeSession(self._sessions).execute(session_id, scope=_scope_for_tenant_id(tenant_id))


class SubmitSessionTurnHandler:
    def __init__(self, *, sessions, worker, governance=None) -> None:
        self._sessions = sessions
        self._worker = worker
        self._governance = governance

    async def handle(
        self,
        command: SubmitSessionTurnCommand,
        *,
        access: RunAccessContext | None = None,
    ) -> str:
        scope = access.scope if access is not None else _scope_for_tenant_id(command.tenant_id)
        if self._sessions.get(command.session_id, scope) is None:
            raise SessionNotFound(command.session_id)
        self._ensure_resource_access(access, "document", command.document_ids)
        if command.portfolio_id is not None:
            self._ensure_resource_access(access, "portfolio", [command.portfolio_id])
        return await self._worker.enqueue_run(
            command.session_id,
            command.message,
            market=command.market,
            language=command.language,
            document_ids=command.document_ids,
            portfolio_id=command.portfolio_id,
            model_policy=_trusted_model_policy(command.model_policy),
            identity_snapshot=(
                snapshot.to_dict()
                if (snapshot := self._trusted_identity_snapshot(access)) is not None
                else command.identity_snapshot
            ),
            idempotency_key=command.idempotency_key,
        )

    async def handle_and_audit(
        self,
        command: SubmitSessionTurnCommand,
        *,
        access: RunAccessContext | None = None,
    ) -> str:
        run_id = await self.handle(command, access=access)
        self._append_run_create_audit(access, run_id, command)
        return run_id

    def _ensure_resource_access(
        self,
        access: RunAccessContext | None,
        resource_type: str,
        resource_ids: list[str],
    ) -> None:
        if access is None or not access.is_enterprise:
            return
        context = access.enterprise_context
        for resource_id in resource_ids:
            if self._resource_allowed(context, resource_type, resource_id):
                continue
            raise PermissionError(f"{resource_type} access denied")

    def _resource_allowed(self, context, resource_type: str, resource_id: str) -> bool:
        if self._governance and self._governance.is_allowed(context, resource_type, resource_id, "read"):
            return True
        if resource_type == "document":
            return resource_id in context.document_acl
        if resource_type == "portfolio":
            return resource_id in context.portfolio_permission
        return True

    def _trusted_identity_snapshot(self, access: RunAccessContext | None) -> IdentitySnapshot | None:
        if access is None or not access.is_enterprise:
            return None
        context = access.enterprise_context
        return IdentitySnapshot(
            tenant_id=context.tenant_id,
            user_hash=context.user_hash,
            role=context.role,
            data_classification=context.data_classification,
            project_id=context.project_id,
            request_id=access.request_id,
            document_acl=tuple(sorted(self._merge_inline_and_persistent(context, "document", "read"))),
            portfolio_permission=tuple(sorted(self._merge_inline_and_persistent(context, "portfolio", "read"))),
            tool_entitlement=tuple(sorted(self._merge_inline_and_persistent(context, "tool", "execute"))),
            approval_authority=tuple(sorted(self._merge_inline_and_persistent(context, "approval", "approve"))),
        )

    def _merge_inline_and_persistent(self, context, resource_type: str, permission: str) -> set[str]:
        inline = {
            "document": context.document_acl,
            "portfolio": context.portfolio_permission,
            "tool": context.tool_entitlement,
            "approval": context.approval_authority,
        }[resource_type]
        if self._governance is None:
            return set(inline)
        return set(inline) | self._governance.list_allowed_resource_ids(
            context,
            resource_type,
            permission,
        )

    def _append_run_create_audit(
        self,
        access: RunAccessContext | None,
        run_id: str,
        command: SubmitSessionTurnCommand,
    ) -> None:
        if access is None or not access.is_enterprise or self._governance is None:
            return
        context = access.enterprise_context
        self._governance.append_audit_event(
            EnterpriseAuditEvent(
                tenant_id=context.tenant_id,
                actor_hash=context.user_hash,
                event_type="run_create",
                resource_type="run",
                resource_id=run_id,
                request_id=access.request_id,
                metadata={
                    "session_id": command.session_id,
                    "document_ids": command.document_ids,
                    "portfolio_id": command.portfolio_id,
                },
            )
        )


def _trusted_model_policy(policy: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in dict(policy).items()
        if key not in IDENTITY_SNAPSHOT_KEYS
    }

"""API query handlers without FastAPI dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from doge.application.use_cases.run_summary import redact_inaccessible_citations
from doge.core.ports.enterprise_governance import EnterpriseAuditEvent


class RunNotFound(KeyError):
    """Raised when a run query cannot find the requested run."""


@dataclass(frozen=True)
class RunAccessContext:
    """Request-derived run access facts without depending on FastAPI."""

    scope: Any
    enterprise_context: Any | None = None
    request_id: str | None = None

    @property
    def is_enterprise(self) -> bool:
        return self.enterprise_context is not None

    @property
    def tenant_id(self) -> str | None:
        if self.enterprise_context is None:
            return None
        return getattr(self.enterprise_context, "tenant_id", None)


class GetRunHandler:
    def __init__(self, *, runtime) -> None:
        self._runtime = runtime

    def handle(self, *, run_id: str, scope=None, access: RunAccessContext | None = None):
        access = access or RunAccessContext(scope=scope)
        run = self._runtime.get_run(access.scope, run_id)
        if run is None or _tenant_mismatch(run, access):
            raise RunNotFound(run_id)
        return run


class ListEventsHandler:
    def __init__(self, *, runtime) -> None:
        self._runtime = runtime

    def handle(
        self,
        *,
        run_id: str,
        scope=None,
        access: RunAccessContext | None = None,
        after_sequence: int = 0,
    ):
        access = access or RunAccessContext(scope=scope)
        GetRunHandler(runtime=self._runtime).handle(run_id=run_id, access=access)
        return [
            event
            for event in self._runtime.list_events(access.scope, run_id)
            if event.sequence > after_sequence
        ]


class ListArtifactsHandler:
    def __init__(self, *, runtime) -> None:
        self._runtime = runtime

    def handle(self, *, run_id: str, scope=None, access: RunAccessContext | None = None):
        access = access or RunAccessContext(scope=scope)
        GetRunHandler(runtime=self._runtime).handle(run_id=run_id, access=access)
        return self._runtime.list_artifacts(access.scope, run_id)


class ListRunsHandler:
    def __init__(self, *, runtime) -> None:
        self._runtime = runtime

    def handle(self, *, scope, session_id: str | None = None, limit: int = 20):
        return self._runtime.list_runs(scope, session_id=session_id, limit=limit)


class GetRunSummaryHandler:
    def __init__(self, *, use_case, governance=None) -> None:
        self._use_case = use_case
        self._governance = governance

    def handle(
        self,
        *,
        run,
        scope=None,
        access: RunAccessContext | None = None,
        audit_event_type: str | None = None,
        audit_resource_type: str = "run",
        audit_resource_id: str | None = None,
    ):
        if access is not None:
            build_scope = access.scope if access.is_enterprise else None
        else:
            build_scope = scope
        result = self._use_case.build(run, scope=build_scope)
        if access is None or not access.is_enterprise or self._governance is None:
            return result
        result = _redact_summary_for_access(result, access, self._governance)
        if audit_event_type is not None:
            self._append_audit_event(
                access,
                event_type=audit_event_type,
                resource_type=audit_resource_type,
                resource_id=audit_resource_id or run.run_id,
            )
        return result

    def _append_audit_event(
        self,
        access: RunAccessContext,
        *,
        event_type: str,
        resource_type: str,
        resource_id: str,
    ) -> None:
        context = access.enterprise_context
        self._governance.append_audit_event(
            EnterpriseAuditEvent(
                tenant_id=context.tenant_id,
                actor_hash=context.user_hash,
                event_type=event_type,
                resource_type=resource_type,
                resource_id=resource_id,
                request_id=access.request_id,
                metadata={},
            )
        )


class ListWorkspaceObjectsHandler:
    def __init__(
        self,
        *,
        workspace_service=None,
        project_service=None,
        research_case_service=None,
        workflow_service=None,
    ) -> None:
        self._services = {
            "workspaces": workspace_service,
            "projects": project_service,
            "research_cases": research_case_service,
            "workflow_templates": workflow_service,
        }

    def handle(self, *, object_type: str, context, limit: int = 100, **filters):
        service = self._services.get(object_type)
        if service is None:
            raise ValueError(f"unsupported workspace object type: {object_type}")
        return service.list(context, limit=limit, **filters)


def _redact_summary_for_access(result: dict, access: RunAccessContext, governance) -> dict:
    context = access.enterprise_context
    document_ids = sorted(
        {
            citation["document_id"]
            for citation in result.get("citations", [])
            if citation.get("document_id")
        }
    )
    allowed = governance.list_allowed_resource_ids(context, "document", "read")
    if "*" in allowed:
        return result
    inline = {
        document_id
        for document_id in document_ids
        if document_id in getattr(context, "document_acl", frozenset())
    }
    return redact_inaccessible_citations(result, (allowed & set(document_ids)) | inline)


def _tenant_mismatch(run, access: RunAccessContext) -> bool:
    if not access.is_enterprise:
        return False
    return _run_tenant_id(run) != access.tenant_id


def _run_tenant_id(run) -> str | None:
    snapshot = getattr(run, "identity_snapshot", None)
    if snapshot is None:
        return None
    return snapshot.tenant_id

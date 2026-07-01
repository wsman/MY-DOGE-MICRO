import hashlib
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from doge.core.domain.agent_models import AgentRun, AgentSession, RunStatus
from doge.core.domain.enterprise_context import IdentitySnapshot
from doge.core.domain.model_policy import ModelPolicy
from doge.core.ports.enterprise_auth import AuthenticatedPrincipal
from doge.core.ports.enterprise_governance import EnterpriseAclGrant, EnterpriseAuditEvent
from doge.application.services.portfolio_import_service import PortfolioImportService
from doge.infrastructure.database.agent_repositories import SQLiteDocumentRepository, SQLiteSessionRepository
from doge.infrastructure.database.enterprise_governance import SQLiteEnterpriseGovernanceRepository
from doge.infrastructure.database.portfolio_repository import SQLitePortfolioRepository
from doge.interfaces.api import deps
from doge.interfaces.api.middleware.tenant_context import TenantContextMiddleware
from doge.interfaces.gateway.routers import audit, documents, enterprise, portfolios, runs, sessions, tools


class _Provider:
    def __init__(self, principal: AuthenticatedPrincipal) -> None:
        self._principal = principal

    def authenticate_bearer(self, token: str) -> AuthenticatedPrincipal:
        return self._principal


class _Worker:
    def __init__(self) -> None:
        self.enqueued: list[dict] = []

    async def enqueue_run(self, session_id: str, message: str, **kwargs):
        self.enqueued.append({
            "session_id": session_id,
            "message": message,
            **kwargs,
        })
        return "run-created"

    async def resolve_approval(
        self,
        run_id: str,
        approval_id: str,
        approved: bool,
        *,
        scope=None,
        tenant_id: str | None = None,
    ):
        assert getattr(scope, "tenant_id", tenant_id) == "tenant-a"
        return AgentRun(
            run_id=run_id,
            workflow="investment_research",
            question="approve",
            model_policy=ModelPolicy(),
            identity_snapshot=IdentitySnapshot(tenant_id="tenant-a", user_hash="user-a"),
            status=RunStatus.QUEUED if approved else RunStatus.AWAITING_APPROVAL,
        )


class _Runtime:
    def __init__(self, tenant_id: str = "tenant-a") -> None:
        self._tenant_id = tenant_id

    def get_run(self, scope, run_id: str | None = None, *, tenant_id: str | None = None):
        if run_id is None:
            run_id = scope
            scope = None
        requested_tenant_id = getattr(scope, "tenant_id", tenant_id)
        if run_id != "run-1":
            return None
        if requested_tenant_id is not None and requested_tenant_id != self._tenant_id:
            return None
        return AgentRun(
            run_id=run_id,
            workflow="investment_research",
            question="approve",
            model_policy=ModelPolicy(),
            identity_snapshot=IdentitySnapshot(tenant_id=self._tenant_id, user_hash="user-a"),
        )


def test_enterprise_document_routes_filter_by_persistent_acl(tmp_path):
    document_repository = SQLiteDocumentRepository(tmp_path / "agent.db")
    governance = SQLiteEnterpriseGovernanceRepository(tmp_path / "agent.db")
    document_repository.save(
        {"document_id": "doc-allowed", "tenant_id": "tenant-a", "filename": "a.txt", "content": "allowed"}
    )
    document_repository.save(
        {"document_id": "doc-denied", "tenant_id": "tenant-a", "filename": "b.txt", "content": "denied"}
    )
    governance.grant(_grant("document", "doc-allowed", "read"))
    app = _app(tmp_path, governance, document_repository=document_repository)

    with TestClient(app) as client:
        listed = client.get("/v1/documents", headers=_headers()).json()["documents"]
        allowed = client.get("/v1/documents/doc-allowed", headers=_headers())
        denied = client.get("/v1/documents/doc-denied", headers=_headers())

    assert [item["document_id"] for item in listed] == ["doc-allowed"]
    assert allowed.status_code == 200
    assert denied.status_code == 403
    audit_types = [event.event_type for event in governance.list_audit_events("tenant-a")]
    assert "document_list" in audit_types
    assert "document_read" in audit_types


def test_enterprise_document_routes_apply_tenant_partition_before_acl(tmp_path):
    document_repository = SQLiteDocumentRepository(tmp_path / "agent.db")
    governance = SQLiteEnterpriseGovernanceRepository(tmp_path / "agent.db")
    document_repository.save(
        {"document_id": "doc-a", "tenant_id": "tenant-a", "filename": "a.txt", "content": "allowed"}
    )
    document_repository.save(
        {"document_id": "doc-b", "tenant_id": "tenant-b", "filename": "b.txt", "content": "other tenant"}
    )
    governance.grant(_grant("document", "doc-a", "read"))
    governance.grant(_grant("document", "doc-b", "read"))
    app = _app(tmp_path, governance, document_repository=document_repository)

    with TestClient(app) as client:
        listed = client.get("/v1/documents", headers=_headers()).json()["documents"]
        hidden = client.get("/v1/documents/doc-b", headers=_headers())

    assert [item["document_id"] for item in listed] == ["doc-a"]
    assert hidden.status_code == 404


def test_enterprise_document_upload_grants_creator_access(tmp_path):
    document_repository = SQLiteDocumentRepository(tmp_path / "agent.db")
    governance = SQLiteEnterpriseGovernanceRepository(tmp_path / "agent.db")
    app = _app(tmp_path, governance, document_repository=document_repository)

    with TestClient(app) as client:
        created = client.post(
            "/v1/documents",
            json={"document_id": "doc-created", "filename": "memo.txt", "content": "memo"},
            headers=_headers(),
        )
        fetched = client.get("/v1/documents/doc-created", headers=_headers())

    assert created.status_code == 200
    assert fetched.status_code == 200
    assert created.json()["tenant_id"] == "tenant-a"
    assert document_repository.get("doc-created", tenant_id="tenant-a") is not None
    assert governance.is_allowed(_context(), "document", "doc-created", "read") is True
    assert governance.is_allowed(_context(), "document", "doc-created", "write") is True


def test_enterprise_tools_route_filters_by_persistent_tool_acl(tmp_path):
    governance = SQLiteEnterpriseGovernanceRepository(tmp_path / "agent.db")
    governance.grant(_grant("tool", "query_stock", "execute"))
    app = _app(tmp_path, governance)

    with TestClient(app) as client:
        response = client.get("/v1/tools", headers=_headers())

    tool_names = [item["function"]["name"] for item in response.json()["tools"]]
    assert tool_names == ["query_stock"]
    assert governance.list_audit_events("tenant-a")[0].event_type == "tool_list"


def test_enterprise_portfolio_import_grants_creator_access(tmp_path):
    governance = SQLiteEnterpriseGovernanceRepository(tmp_path / "agent.db")
    portfolio_repository = SQLitePortfolioRepository(tmp_path / "agent.db")
    app = _app(tmp_path, governance, portfolio_repository=portfolio_repository)
    csv_payload = (
        "symbol,asset_class,sector,quantity,market_value,currency\n"
        "AAPL,equity,technology,10,2500,USD\n"
    )

    with TestClient(app) as client:
        response = client.post(
            "/v1/portfolios/import",
            data={"portfolio_id": "portfolio-created", "name": "Creator book"},
            files={"file": ("portfolio.csv", csv_payload.encode("utf-8"), "text/csv")},
            headers=_headers(),
        )

    assert response.status_code == 200
    assert response.json()["tenant_id"] == "tenant-a"
    assert portfolio_repository.get("portfolio-created", tenant_id="tenant-a") is not None
    assert portfolio_repository.get("portfolio-created", tenant_id="tenant-b") is None
    assert governance.is_allowed(_context(), "portfolio", "portfolio-created", "read") is True
    assert governance.is_allowed(_context(), "portfolio", "portfolio-created", "write") is True
    assert governance.list_audit_events("tenant-a")[0].event_type == "portfolio_import"


def test_enterprise_approval_route_requires_authority_and_records_actor(tmp_path):
    governance = SQLiteEnterpriseGovernanceRepository(tmp_path / "agent.db")
    governance.grant(_grant("approval", "appr-1", "approve"))
    app = _app(tmp_path, governance)

    with TestClient(app) as client:
        response = client.post(
            "/v1/runs/run-1/approvals/appr-1",
            json={"approved": True},
            headers=_headers(request_id="req-approval"),
        )

    assert response.status_code == 202
    decisions = governance.list_approval_decisions("appr-1")
    assert len(decisions) == 1
    assert decisions[0].tenant_id == "tenant-a"
    assert decisions[0].actor_hash == "user-a"
    assert decisions[0].request_id == "req-approval"
    assert decisions[0].decision == "approved"


def test_enterprise_approval_route_denies_missing_authority(tmp_path):
    governance = SQLiteEnterpriseGovernanceRepository(tmp_path / "agent.db")
    app = _app(tmp_path, governance)

    with TestClient(app) as client:
        response = client.post(
            "/v1/runs/run-1/approvals/appr-1",
            json={"approved": True},
            headers=_headers(),
        )

    assert response.status_code == 403
    assert governance.list_approval_decisions("appr-1") == []


def test_enterprise_run_routes_hide_cross_tenant_runs(tmp_path):
    governance = SQLiteEnterpriseGovernanceRepository(tmp_path / "agent.db")
    app = _app(tmp_path, governance, runtime_tenant_id="tenant-b")

    with TestClient(app) as client:
        response = client.get("/v1/runs/run-1", headers=_headers())

    assert response.status_code == 404


def test_enterprise_session_routes_apply_tenant_partition(tmp_path):
    governance = SQLiteEnterpriseGovernanceRepository(tmp_path / "agent.db")
    session_repository = SQLiteSessionRepository(tmp_path / "agent.db")
    session_a = AgentSession.create("Tenant A", tenant_id="tenant-a")
    session_b = AgentSession.create("Tenant B", tenant_id="tenant-b")
    session_repository.save(session_a)
    session_repository.save(session_b)
    app = _app(tmp_path, governance, session_repository=session_repository)

    with TestClient(app) as client:
        listed = client.get("/v1/sessions", headers=_headers())
        hidden = client.get(f"/v1/sessions/{session_b.session_id}", headers=_headers())

    assert listed.status_code == 200
    assert [item["session_id"] for item in listed.json()["sessions"]] == [session_a.session_id]
    assert hidden.status_code == 404


def test_enterprise_turn_creation_uses_trusted_identity_snapshot(tmp_path):
    governance = SQLiteEnterpriseGovernanceRepository(tmp_path / "agent.db")
    session_repository = SQLiteSessionRepository(tmp_path / "agent.db")
    session = AgentSession.create("Tenant A", tenant_id="tenant-a")
    session_repository.save(session)
    worker = _Worker()
    app = _app(tmp_path, governance, session_repository=session_repository, worker=worker)

    with TestClient(app) as client:
        response = client.post(
            f"/v1/sessions/{session.session_id}/turns",
            headers=_headers("req-trusted"),
            json={
                "message": "Analyze",
                "portfolio_id": None,
                "model_policy": {
                    "tenant_id": "tenant-spoofed",
                    "user_hash": "user-spoofed",
                    "request_id": "req-spoofed",
                    "max_tool_rounds": 3,
                },
            },
        )

    assert response.status_code == 202
    assert worker.enqueued[0]["model_policy"] == {"max_tool_rounds": 3}
    assert worker.enqueued[0]["identity_snapshot"]["tenant_id"] == "tenant-a"
    assert worker.enqueued[0]["identity_snapshot"]["user_hash"] == "user-a"
    assert worker.enqueued[0]["identity_snapshot"]["request_id"] == "req-trusted"


def test_enterprise_audit_route_exports_only_current_tenant(tmp_path):
    governance = SQLiteEnterpriseGovernanceRepository(tmp_path / "agent.db")
    governance.append_audit_event(
        EnterpriseAuditEvent(
            tenant_id="tenant-a",
            actor_hash="user-a",
            event_type="tool_execute",
            resource_type="tool",
            resource_id="query_stock",
        )
    )
    governance.append_audit_event(
        EnterpriseAuditEvent(
            tenant_id="tenant-b",
            actor_hash="user-b",
            event_type="tool_execute",
            resource_type="tool",
            resource_id="query_stock",
        )
    )
    app = _app(tmp_path, governance)

    with TestClient(app) as client:
        response = client.get("/v1/audit/events?tenant_id=tenant-b", headers=_headers())

    assert response.status_code == 200
    events = response.json()["events"]
    assert len(events) == 1
    assert events[0]["tenant_id"] == "tenant-a"
    assert events[0]["event_type"] == "tool_execute"


def test_enterprise_audit_jsonl_export_is_tenant_scoped_and_redacted(tmp_path):
    governance = SQLiteEnterpriseGovernanceRepository(tmp_path / "agent.db")
    governance.append_audit_event(
        EnterpriseAuditEvent(
            tenant_id="tenant-a",
            actor_hash="user-a",
            event_type="model_route",
            resource_type="run",
            resource_id="run-1",
            metadata={
                "api_key": "sk-secret",
                "nested": {"authorization": "Bearer secret-token", "safe": "ok"},
                "message": (
                    "provider failed Authorization: Bearer live-token "
                    "MOONSHOT_API_KEY=moonshot-secret sk-live-secret"
                ),
            },
        )
    )
    governance.append_audit_event(
        EnterpriseAuditEvent(
            tenant_id="tenant-b",
            actor_hash="user-b",
            event_type="model_route",
            resource_type="run",
            resource_id="run-2",
            metadata={"safe": "other"},
        )
    )
    app = _app(tmp_path, governance, roles=("tenant_admin",))

    with TestClient(app) as client:
        response = client.get("/v1/audit/events/export?tenant_id=tenant-b", headers=_headers())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    assert response.headers["x-doge-audit-export-schema"] == "doge.audit_export_manifest.v1"
    assert response.headers["x-doge-audit-content-schema"] == "doge.audit_event_jsonl.v1"
    assert response.headers["x-doge-audit-sha256"] == hashlib.sha256(response.content).hexdigest()
    assert response.headers["x-doge-audit-byte-count"] == str(len(response.content))
    assert response.headers["x-doge-audit-line-count"] == "1"
    assert response.headers["x-doge-audit-event-count"] == "1"
    assert response.headers["x-doge-audit-generated-at"].endswith("+00:00")
    rows = [json.loads(line) for line in response.text.splitlines()]
    assert len(rows) == 1
    assert rows[0]["tenant_id"] == "tenant-a"
    assert rows[0]["resource_id"] == "run-1"
    assert rows[0]["metadata"]["api_key"] == "<redacted>"
    assert rows[0]["metadata"]["nested"]["authorization"] == "<redacted>"
    assert rows[0]["metadata"]["nested"]["safe"] == "ok"
    assert "live-token" not in response.text
    assert "moonshot-secret" not in response.text
    assert "sk-live-secret" not in response.text
    assert "Bearer [REDACTED]" in response.text
    assert "MOONSHOT_API_KEY=<redacted>" in response.text
    assert "sk-[REDACTED]" in response.text
    audit_types = [event.event_type for event in governance.list_audit_events("tenant-a")]
    assert "audit_export" in audit_types


def test_enterprise_audit_jsonl_export_rejects_non_admin_role(tmp_path):
    governance = SQLiteEnterpriseGovernanceRepository(tmp_path / "agent.db")
    app = _app(tmp_path, governance, roles=("analyst",))

    with TestClient(app) as client:
        response = client.get("/v1/audit/events/export", headers=_headers())

    assert response.status_code == 403


def test_enterprise_audit_retention_purge_is_tenant_scoped_and_audited(tmp_path):
    governance = SQLiteEnterpriseGovernanceRepository(tmp_path / "agent.db")
    governance.append_audit_event(
        EnterpriseAuditEvent(
            tenant_id="tenant-a",
            actor_hash="user-a",
            event_type="old_a",
            resource_type="run",
            resource_id="run-old-a",
            created_at="2020-01-01T00:00:00+00:00",
        )
    )
    governance.append_audit_event(
        EnterpriseAuditEvent(
            tenant_id="tenant-a",
            actor_hash="user-a",
            event_type="new_a",
            resource_type="run",
            resource_id="run-new-a",
            created_at="2999-01-01T00:00:00+00:00",
        )
    )
    governance.append_audit_event(
        EnterpriseAuditEvent(
            tenant_id="tenant-b",
            actor_hash="user-b",
            event_type="old_b",
            resource_type="run",
            resource_id="run-old-b",
            created_at="2020-01-01T00:00:00+00:00",
        )
    )
    app = _app(tmp_path, governance, roles=("tenant_admin",))

    with TestClient(app) as client:
        response = client.post("/v1/audit/events/retention?retention_days=1", headers=_headers())

    assert response.status_code == 200
    assert response.json()["deleted"] == 1
    assert response.json()["retention_days"] == 1
    tenant_a_types = [event.event_type for event in governance.list_audit_events("tenant-a")]
    assert "old_a" not in tenant_a_types
    assert "new_a" in tenant_a_types
    assert "audit_retention_purge" in tenant_a_types
    assert [event.event_type for event in governance.list_audit_events("tenant-b")] == ["old_b"]


def test_enterprise_audit_retention_purge_rejects_non_admin_role(tmp_path):
    governance = SQLiteEnterpriseGovernanceRepository(tmp_path / "agent.db")
    app = _app(tmp_path, governance, roles=("analyst",))

    with TestClient(app) as client:
        response = client.post("/v1/audit/events/retention", headers=_headers())

    assert response.status_code == 403


def test_enterprise_acl_admin_routes_manage_current_tenant_only(tmp_path):
    governance = SQLiteEnterpriseGovernanceRepository(tmp_path / "agent.db")
    governance.grant(
        EnterpriseAclGrant(
            tenant_id="tenant-b",
            subject_hash="user-a",
            resource_type="tool",
            resource_id="query_stock",
            permission="execute",
            provenance="other-tenant",
        )
    )
    app = _app(tmp_path, governance, roles=("tenant_admin",))

    with TestClient(app) as client:
        created = client.post(
            "/v1/enterprise/acl/grants",
            json={
                "subject_hash": "analyst-a",
                "resource_type": "document",
                "resource_id": "doc-1",
                "permission": "read",
                "provenance": "test-admin",
            },
            headers=_headers(request_id="req-acl"),
        )
        listed = client.get("/v1/enterprise/acl/grants", headers=_headers(request_id="req-list"))
        deleted = client.delete(
            "/v1/enterprise/acl/grants",
            params={
                "subject_hash": "analyst-a",
                "resource_type": "document",
                "resource_id": "doc-1",
                "permission": "read",
            },
            headers=_headers(request_id="req-delete"),
        )

    assert created.status_code == 201
    assert created.json()["tenant_id"] == "tenant-a"
    assert listed.status_code == 200
    assert [grant["tenant_id"] for grant in listed.json()["grants"]] == ["tenant-a"]
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True
    assert governance.list_acl_grants(tenant_id="tenant-a") == []
    assert len(governance.list_acl_grants(tenant_id="tenant-b")) == 1
    audit_types = [event.event_type for event in governance.list_audit_events("tenant-a")]
    assert {"acl_grant", "acl_list", "acl_revoke"}.issubset(audit_types)


def test_enterprise_acl_admin_routes_reject_non_admin_role(tmp_path):
    governance = SQLiteEnterpriseGovernanceRepository(tmp_path / "agent.db")
    app = _app(tmp_path, governance, roles=("analyst",))

    with TestClient(app) as client:
        response = client.post(
            "/v1/enterprise/acl/grants",
            json={
                "subject_hash": "analyst-a",
                "resource_type": "document",
                "resource_id": "doc-1",
                "permission": "read",
            },
            headers=_headers(),
        )

    assert response.status_code == 403
    assert governance.list_acl_grants(tenant_id="tenant-a") == []


def _app(
    tmp_path,
    governance: SQLiteEnterpriseGovernanceRepository,
    *,
    document_repository: SQLiteDocumentRepository | None = None,
    session_repository: SQLiteSessionRepository | None = None,
    portfolio_repository: SQLitePortfolioRepository | None = None,
    worker: _Worker | None = None,
    tenant_id: str = "tenant-a",
    runtime_tenant_id: str | None = None,
    roles: tuple[str, ...] = ("portfolio_manager",),
) -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        TenantContextMiddleware,
        local_demo=False,
        auth_provider=_Provider(
            AuthenticatedPrincipal(
                subject_hash="user-a",
                tenant_id=tenant_id,
                roles=roles,
            )
        ),
    )
    app.include_router(documents.router, prefix="/v1")
    app.include_router(portfolios.router, prefix="/v1")
    app.include_router(tools.router, prefix="/v1")
    app.include_router(sessions.router, prefix="/v1")
    app.include_router(runs.router, prefix="/v1")
    app.include_router(audit.router, prefix="/v1")
    app.include_router(enterprise.router, prefix="/v1")
    app.dependency_overrides[deps.get_enterprise_governance_repository] = lambda: governance
    if document_repository is not None:
        app.dependency_overrides[deps.get_agent_document_repository] = lambda: document_repository
        from doge.application.services.file_upload_service import FileUploadService

        app.dependency_overrides[deps.get_file_upload_service] = lambda: FileUploadService(
            document_repository,
            storage_dir=tmp_path / "documents",
        )
    if session_repository is not None:
        app.dependency_overrides[deps.get_agent_session_repository] = lambda: session_repository
    if portfolio_repository is not None:
        app.dependency_overrides[deps.get_portfolio_repository] = lambda: portfolio_repository
        app.dependency_overrides[deps.get_portfolio_import_service] = lambda: PortfolioImportService(
            portfolio_repository
        )
    app.dependency_overrides[deps.get_persisted_research_agent_runtime] = lambda: _Runtime(
        tenant_id=runtime_tenant_id or tenant_id
    )
    app.dependency_overrides[deps.get_daemon_worker] = lambda: worker or _Worker()
    return app


def _grant(resource_type: str, resource_id: str, permission: str) -> EnterpriseAclGrant:
    return EnterpriseAclGrant(
        tenant_id="tenant-a",
        subject_hash="user-a",
        resource_type=resource_type,
        resource_id=resource_id,
        permission=permission,
        provenance="test",
    )


def _context():
    from doge.core.domain.enterprise_context import EnterpriseContext

    return EnterpriseContext(tenant_id="tenant-a", user_hash="user-a")


def _headers(request_id: str = "req-test") -> dict[str, str]:
    return {"Authorization": "Bearer token", "X-Request-ID": request_id}

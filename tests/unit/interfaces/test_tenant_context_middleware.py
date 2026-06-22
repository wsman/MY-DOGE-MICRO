from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from doge.interfaces.api.middleware.tenant_context import (
    TenantContextMiddleware,
    enterprise_context_from_headers,
)
from doge.core.ports.enterprise_auth import AuthenticatedPrincipal, EnterpriseAuthError


class _FakeEnterpriseAuthProvider:
    def authenticate_bearer(self, token: str) -> AuthenticatedPrincipal:
        if token != "valid-token":
            raise EnterpriseAuthError("bad token")
        return AuthenticatedPrincipal(
            subject_hash="trusted-subject-hash",
            tenant_id="tenant-trusted",
            roles=("portfolio_manager",),
            entitlements=("tool-risk", "tool-evidence"),
            document_acl=("doc-trusted",),
            portfolio_permission=("portfolio-trusted",),
            approval_authority=("publish-memo",),
            data_classification="confidential",
            project_id="project-alpha",
        )


def test_enterprise_context_from_headers_hashes_user_identifier():
    context = enterprise_context_from_headers({
        "x-doge-tenant-id": "tenant-a",
        "x-doge-user-id": "analyst@example.com",
        "x-doge-role": "portfolio_manager",
        "x-doge-document-acl": "doc-1,doc-2",
        "x-doge-portfolio-permission": "portfolio-demo",
    })

    assert context.tenant_id == "tenant-a"
    assert context.user_hash != "analyst@example.com"
    assert context.role == "portfolio_manager"
    assert context.can_access_document("doc-1") is True
    assert context.can_access_document("doc-3") is False
    assert context.can_access_portfolio("portfolio-demo") is True


def test_tenant_context_middleware_rejects_enterprise_without_auth():
    app = FastAPI()
    app.add_middleware(TenantContextMiddleware, local_demo=False)

    @app.get("/health")
    def health():
        return {"ok": True}

    response = TestClient(app).get("/health")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_tenant_context_middleware_attaches_local_demo_context():
    app = FastAPI()
    app.add_middleware(TenantContextMiddleware, local_demo=True)

    @app.get("/tenant")
    def tenant(request: Request):
        return {"tenant_id": request.state.enterprise_context.tenant_id}

    response = TestClient(app).get("/tenant", headers={"x-doge-tenant-id": "tenant-a"})

    assert response.status_code == 200
    assert response.json() == {"tenant_id": "tenant-a"}


def test_tenant_context_middleware_rejects_missing_bearer_with_auth_provider():
    app = FastAPI()
    app.add_middleware(
        TenantContextMiddleware,
        local_demo=False,
        auth_provider=_FakeEnterpriseAuthProvider(),
    )

    @app.get("/tenant")
    def tenant(request: Request):
        return {"tenant_id": request.state.enterprise_context.tenant_id}

    response = TestClient(app).get("/tenant")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_tenant_context_middleware_maps_trusted_principal():
    app = FastAPI()
    app.add_middleware(
        TenantContextMiddleware,
        local_demo=False,
        auth_provider=_FakeEnterpriseAuthProvider(),
    )

    @app.get("/tenant")
    def tenant(request: Request):
        context = request.state.enterprise_context
        return {
            "tenant_id": context.tenant_id,
            "user_hash": context.user_hash,
            "role": context.role,
            "can_access_trusted_doc": context.can_access_document("doc-trusted"),
            "can_access_header_doc": context.can_access_document("doc-from-header"),
            "can_access_portfolio": context.can_access_portfolio("portfolio-trusted"),
            "tool_entitlement": sorted(context.tool_entitlement),
            "approval_authority": sorted(context.approval_authority),
            "data_classification": context.data_classification,
            "project_id": context.project_id,
        }

    response = TestClient(app).get(
        "/tenant",
        headers={
            "authorization": "Bearer valid-token",
            "x-doge-tenant-id": "tenant-forged",
            "x-doge-user-id": "attacker@example.com",
            "x-doge-document-acl": "doc-from-header",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "tenant_id": "tenant-trusted",
        "user_hash": "trusted-subject-hash",
        "role": "portfolio_manager",
        "can_access_trusted_doc": True,
        "can_access_header_doc": False,
        "can_access_portfolio": True,
        "tool_entitlement": ["tool-evidence", "tool-risk"],
        "approval_authority": ["publish-memo"],
        "data_classification": "confidential",
        "project_id": "project-alpha",
    }


def test_tenant_context_middleware_rejects_invalid_bearer():
    app = FastAPI()
    app.add_middleware(
        TenantContextMiddleware,
        local_demo=False,
        auth_provider=_FakeEnterpriseAuthProvider(),
    )

    @app.get("/tenant")
    def tenant(request: Request):
        return {"tenant_id": request.state.enterprise_context.tenant_id}

    response = TestClient(app).get("/tenant", headers={"authorization": "Bearer wrong"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"

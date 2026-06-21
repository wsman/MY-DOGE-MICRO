from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from doge.interfaces.api.middleware.tenant_context import (
    TenantContextMiddleware,
    enterprise_context_from_headers,
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

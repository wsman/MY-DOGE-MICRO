from fastapi import FastAPI
from fastapi.testclient import TestClient

from doge.config import Settings
from doge.config.settings import FeatureConfig
from doge.core.domain.agent_models import AgentRun
from doge.core.domain.platform_models import Workspace
from doge.core.ports.enterprise_auth import AuthenticatedPrincipal
from doge.infrastructure.database.enterprise_governance import SQLiteEnterpriseGovernanceRepository
from doge.infrastructure.database.platform_repository import SQLitePlatformRepository
from doge.interfaces.api import deps
from doge.interfaces.api.middleware.tenant_context import TenantContextMiddleware
from doge.interfaces.api.routers.v1 import platform


def test_platform_objects_api_is_feature_flagged(tmp_path):
    app = _app(tmp_path, platform_enabled=False)

    with TestClient(app) as client:
        response = client.get("/v1/workspaces")

    assert response.status_code == 404
    assert response.json()["detail"] == "platform objects API disabled"


def test_platform_api_creates_hierarchy_and_links_run(tmp_path):
    app = _app(tmp_path, platform_enabled=True, templates_enabled=True)

    with TestClient(app) as client:
        workspace = client.post("/v1/workspaces", json={"name": "Local Research"}).json()
        project = client.post(
            "/v1/projects",
            json={"workspace_id": workspace["workspace_id"], "name": "Semis", "default_market": "us"},
        ).json()
        case = client.post(
            "/v1/research-cases",
            json={"project_id": project["project_id"], "title": "NVDA diligence"},
        ).json()
        linked = client.post(
            f"/v1/research-cases/{case['case_id']}/runs",
            json={"run_id": "run-1"},
        ).json()
        template = client.post(
            "/v1/workflow-templates",
            json={"slug": "stock-diligence", "name": "Stock diligence"},
        ).json()
        templates = client.get("/v1/workflow-templates").json()["workflow_templates"]

    assert workspace["name"] == "Local Research"
    assert project["workspace_id"] == workspace["workspace_id"]
    assert case["project_id"] == project["project_id"]
    assert linked["run_id"] == "run-1"
    assert template["slug"] == "stock-diligence"
    assert [item["template_id"] for item in templates] == [template["template_id"]]


def test_research_case_run_can_be_created_from_workflow_template(tmp_path):
    runtime = _Runtime()
    app = _app(tmp_path, platform_enabled=True, templates_enabled=True, runtime=runtime)

    with TestClient(app) as client:
        workspace = client.post("/v1/workspaces", json={"name": "Local Research"}).json()
        project = client.post(
            "/v1/projects",
            json={"workspace_id": workspace["workspace_id"], "name": "Semis"},
        ).json()
        case = client.post(
            "/v1/research-cases",
            json={"project_id": project["project_id"], "title": "NVDA diligence"},
        ).json()
        template = client.post(
            "/v1/workflow-templates",
            json={
                "slug": "earnings-review",
                "name": "Earnings review",
                "tool_policy": {
                    "model_policy": {"execution_profile": "financial_research", "max_tool_rounds": 5},
                    "max_tokens": 4096,
                },
            },
        ).json()
        linked = client.post(
            f"/v1/research-cases/{case['case_id']}/runs",
            json={
                "template_id": template["template_id"],
                "question": "Analyze NVDA Q1",
                "model_policy": {"max_tool_rounds": 3},
                "inputs": {"ticker": "NVDA"},
            },
        ).json()

    assert linked["run_id"] == "run-created-1"
    assert linked["template_id"] == template["template_id"]
    assert runtime.created_requests[0]["workflow"] == "earnings-review"
    assert runtime.created_requests[0]["question"] == "Analyze NVDA Q1"
    assert runtime.created_requests[0]["model_policy"]["execution_profile"] == "financial_research"
    assert runtime.created_requests[0]["model_policy"]["max_tool_rounds"] == 3
    assert runtime.created_requests[0]["model_policy"]["max_tokens"] == 4096
    assert runtime.created_requests[0]["model_policy"]["template_slug"] == "earnings-review"
    assert runtime.created_requests[0]["template"]["inputs"] == {"ticker": "NVDA"}


def test_research_case_template_run_requires_template_flag(tmp_path):
    app = _app(tmp_path, platform_enabled=True, templates_enabled=False)

    with TestClient(app) as client:
        workspace = client.post("/v1/workspaces", json={"name": "Local Research"}).json()
        project = client.post(
            "/v1/projects",
            json={"workspace_id": workspace["workspace_id"], "name": "Semis"},
        ).json()
        case = client.post(
            "/v1/research-cases",
            json={"project_id": project["project_id"], "title": "NVDA diligence"},
        ).json()
        response = client.post(
            f"/v1/research-cases/{case['case_id']}/runs",
            json={"template_id": "tpl-unknown"},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "workflow templates API disabled"


def test_enterprise_platform_list_filters_by_acl(tmp_path):
    repo = SQLitePlatformRepository(tmp_path / "agent.db")
    governance = SQLiteEnterpriseGovernanceRepository(tmp_path / "agent.db")
    allowed = Workspace.create(name="Allowed", tenant_id="tenant-a")
    denied = Workspace.create(name="Denied", tenant_id="tenant-a")
    repo.save_workspace(allowed)
    repo.save_workspace(denied)
    governance.grant(_grant("workspace", allowed.workspace_id, "read"))
    app = _app(tmp_path, platform_enabled=True, repo=repo, governance=governance, enterprise=True)

    with TestClient(app) as client:
        response = client.get("/v1/workspaces", headers={"Authorization": "Bearer token"})

    assert response.status_code == 200
    assert [item["workspace_id"] for item in response.json()["workspaces"]] == [allowed.workspace_id]


def test_capability_registry_api_is_feature_flagged(tmp_path):
    app = _app(tmp_path, platform_enabled=False, capability_enabled=False)

    with TestClient(app) as client:
        response = client.get("/v1/capabilities")

    assert response.status_code == 404
    assert response.json()["detail"] == "capability registry API disabled"


def test_capability_registry_api_returns_redacted_snapshot(tmp_path, monkeypatch):
    monkeypatch.setenv("MOONSHOT_API_KEY", "moonshot-secret")
    app = _app(tmp_path, platform_enabled=False, capability_enabled=True)

    with TestClient(app) as client:
        response = client.get("/v1/capabilities")

    assert response.status_code == 200
    body = response.json()
    assert body["snapshot_id"].startswith("cap-")
    assert "moonshot-secret" not in repr(body)
    capabilities = {item["capability_id"]: item for item in body["capabilities"]}
    assert capabilities["maturity.production_ready"]["status"] == "blocked"
    assert capabilities["feature.capability_registry"]["metadata"]["lifecycle"]["env_var"] == (
        "DOGE_FEATURE_CAPABILITY_REGISTRY"
    )
    assert capabilities["feature.platform_objects"]["metadata"]["lifecycle"]["current_default"] is False


def _app(
    tmp_path,
    *,
    platform_enabled: bool,
    templates_enabled: bool = False,
    capability_enabled: bool = False,
    repo: SQLitePlatformRepository | None = None,
    governance: SQLiteEnterpriseGovernanceRepository | None = None,
    enterprise: bool = False,
    runtime=None,
) -> FastAPI:
    app = FastAPI()
    if enterprise:
        app.add_middleware(TenantContextMiddleware, local_demo=False, auth_provider=_Provider())
    app.include_router(platform.router, prefix="/v1")
    repo = repo or SQLitePlatformRepository(tmp_path / "agent.db")
    governance = governance or SQLiteEnterpriseGovernanceRepository(tmp_path / "agent.db")
    app.dependency_overrides[deps.get_settings_dep] = lambda: Settings(
        features=FeatureConfig(
            platform_objects=platform_enabled,
            workflow_templates=templates_enabled,
            capability_registry=capability_enabled,
        )
    )
    app.dependency_overrides[deps.get_platform_repository] = lambda: repo
    app.dependency_overrides[deps.get_enterprise_governance_repository] = lambda: governance
    runtime = runtime or _Runtime()
    app.dependency_overrides[deps.get_persisted_research_agent_runtime] = lambda: runtime
    return app


class _Provider:
    def authenticate_bearer(self, token: str) -> AuthenticatedPrincipal:
        return AuthenticatedPrincipal(subject_hash="user-a", tenant_id="tenant-a", roles=("analyst",))


class _Runtime:
    def __init__(self):
        self.created_requests = []

    async def create_run(self, request):
        self.created_requests.append(request)
        return AgentRun.create(
            workflow=request.get("workflow", "investment_research"),
            question=request.get("question", "Analyze"),
            run_id=f"run-created-{len(self.created_requests)}",
            model_policy=request.get("model_policy"),
        )

    def get_run(self, run_id):
        if run_id != "run-1":
            return None
        return AgentRun.create(workflow="investment_research", question="Analyze", run_id=run_id)


def _grant(resource_type: str, resource_id: str, permission: str):
    from doge.core.ports.enterprise_governance import EnterpriseAclGrant

    return EnterpriseAclGrant(
        tenant_id="tenant-a",
        subject_hash="user-a",
        resource_type=resource_type,
        resource_id=resource_id,
        permission=permission,
        provenance="test",
    )

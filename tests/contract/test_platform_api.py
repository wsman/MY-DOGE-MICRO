from fastapi import FastAPI
from fastapi.testclient import TestClient

from doge.config import Settings
from doge.config.settings import FeatureConfig
from doge.core.domain.agent_models import AgentRun, RunStatus
from doge.core.domain.platform_models import Workspace
from doge.core.domain.portfolio_models import Portfolio
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
    assert "template_slug" not in runtime.created_requests[0]["model_policy"]
    assert runtime.created_requests[0]["workflow_context"]["template_slug"] == "earnings-review"
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


def test_research_case_execution_preflight_and_execute_records_execution(tmp_path):
    runtime = _Runtime()
    app = _app(
        tmp_path,
        platform_enabled=True,
        templates_enabled=True,
        run_summary_enabled=True,
        runtime=runtime,
    )

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
                "input_schema": {
                    "required": ["ticker"],
                    "properties": {"ticker": {"type": "string"}},
                },
                "required_capabilities": ["feature.workflow_templates"],
            },
        ).json()

        invalid = client.post(
            f"/v1/research-cases/{case['case_id']}/executions/preflight",
            json={"template_id": template["template_id"], "inputs": {}},
        ).json()
        valid = client.post(
            f"/v1/research-cases/{case['case_id']}/executions/preflight",
            json={"template_id": template["template_id"], "inputs": {"ticker": "NVDA"}},
        ).json()
        executed = client.post(
            f"/v1/research-cases/{case['case_id']}/executions",
            json={
                "template_id": template["template_id"],
                "inputs": {"ticker": "NVDA"},
                "document_ids": ["doc-1"],
                "portfolio_id": "portfolio-demo",
            },
        ).json()
        executions = client.get(f"/v1/research-cases/{case['case_id']}/executions").json()["executions"]
        review = client.get(f"/v1/research-cases/{case['case_id']}/review").json()

    assert invalid["valid"] is False
    assert invalid["input_errors"][0]["code"] == "required"
    assert valid["valid"] is True
    assert executed["execution_id"].startswith("exec-")
    assert executed["run_id"] == "run-created-1"
    assert executed["status"] == "queued"
    assert executed["links"]["run"] == "/v1/runs/run-created-1"
    assert executions[0]["execution_id"] == executed["execution_id"]
    assert review["approvals"][0]["approval_id"].startswith("appr-")
    assert review["approvals"][0]["action"] == "publish memo"
    assert review["approvals"][0]["status"] == "pending"


def test_research_case_assets_decisions_and_review(tmp_path):
    runtime = _Runtime()
    app = _app(tmp_path, platform_enabled=True, templates_enabled=True, run_summary_enabled=True, runtime=runtime)

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
        asset = client.post(
            f"/v1/research-cases/{case['case_id']}/assets",
            json={"asset_type": "document", "asset_id": "doc-1", "asset_name": "10-Q"},
        ).json()
        assets = client.get(f"/v1/research-cases/{case['case_id']}/assets").json()["assets"]
        decision = client.post(
            f"/v1/research-cases/{case['case_id']}/decisions",
            json={"decision_type": "hold", "rationale": "Needs second source."},
        ).json()
        decisions = client.get(f"/v1/research-cases/{case['case_id']}/decisions").json()["decisions"]
        review = client.get(f"/v1/research-cases/{case['case_id']}/review").json()

    assert asset["asset_link_id"].startswith("cal-")
    assert assets[0]["asset_id"] == "doc-1"
    assert decision["decision_id"].startswith("dec-")
    assert decisions[0]["decision_type"] == "hold"
    assert review["case"]["case_id"] == case["case_id"]
    assert review["assets"][0]["asset_link_id"] == asset["asset_link_id"]


def test_home_queue_returns_actionable_case_items(tmp_path):
    app = _app(tmp_path, platform_enabled=True, templates_enabled=True)

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
        queue = client.get("/v1/home-queue").json()

    assert queue["pending_cases"][0]["case"]["case_id"] == case["case_id"]
    assert queue["pending_cases"][0]["reason"] == "no_recent_execution"
    assert queue["data_freshness"] is None
    assert "data_freshness_unavailable" in queue["warnings"]


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
    run_summary_enabled: bool = False,
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
            run_summary_api=run_summary_enabled,
        )
    )
    app.dependency_overrides[deps.get_platform_repository] = lambda: repo
    app.dependency_overrides[deps.get_enterprise_governance_repository] = lambda: governance
    runtime = runtime or _Runtime()
    app.dependency_overrides[deps.get_persisted_research_agent_runtime] = lambda: runtime
    app.dependency_overrides[deps.get_agent_document_repository] = lambda: _DocumentRepo()
    app.dependency_overrides[deps.get_portfolio_repository] = lambda: _PortfolioRepo()
    app.dependency_overrides[deps.get_daemon_worker] = lambda: _Worker(runtime)
    return app


class _Provider:
    def authenticate_bearer(self, token: str) -> AuthenticatedPrincipal:
        return AuthenticatedPrincipal(subject_hash="user-a", tenant_id="tenant-a", roles=("analyst",))


class _Runtime:
    def __init__(self):
        self.created_requests = []
        self.runs = {
            "run-1": AgentRun.create(workflow="investment_research", question="Analyze", run_id="run-1")
        }

    async def create_run(self, request, *, tenant_id=None):
        self.created_requests.append(request)
        run = AgentRun.create(
            workflow=request.get("workflow", "investment_research"),
            question=request.get("question", "Analyze"),
            run_id=f"run-created-{len(self.created_requests)}",
            model_policy=request.get("model_policy"),
            workflow_context=request.get("workflow_context"),
            identity_snapshot=request.get("identity_snapshot"),
        )
        run.add_approval("publish memo", "high")
        self.runs[run.run_id] = run
        return run

    def get_run(self, scope, run_id=None, *, tenant_id=None):
        if run_id is None:
            run_id = scope
        return self.runs.get(run_id)

    async def run_to_pause_or_completion(self, run_id, *, tenant_id=None):
        run = self.runs[run_id]
        run.status = RunStatus.COMPLETED
        return run

    def list_runs(self, scope=None, session_id=None, limit=20, *, tenant_id=None):
        return list(self.runs.values())[:limit]

    def list_artifacts(self, scope, run_id=None, *, tenant_id=None):
        if run_id is None:
            run_id = scope
        run = self.runs.get(run_id)
        return list(run.artifacts) if run is not None else []


class _Worker:
    def __init__(self, runtime):
        self._runtime = runtime

    async def enqueue_continuation(self, run_id, *, scope=None, tenant_id=None):
        run = self._runtime.runs[run_id]
        run.status = RunStatus.QUEUED


class _DocumentRepo:
    def get(self, document_id, tenant_id=None):
        if document_id == "doc-1":
            return {"document_id": "doc-1", "filename": "10-Q", "tenant_id": tenant_id}
        return None

    def save(self, document):
        return None

    def get_by_hash(self, file_hash, tenant_id=None):
        return None

    def list_recent(self, limit=100, tenant_id=None):
        return []


class _PortfolioRepo:
    def get(self, portfolio_id, tenant_id=None):
        if portfolio_id == "portfolio-demo":
            return Portfolio(portfolio_id="portfolio-demo", name="Demo")
        return None

    def save(self, portfolio, tenant_id=None):
        return None


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

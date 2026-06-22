from fastapi import FastAPI
from fastapi.testclient import TestClient

from doge.config import Settings
from doge.application.use_cases.run_summary import BuildRunSummary
from doge.config.settings import FeatureConfig
from doge.core.domain.agent_models import AgentArtifact, AgentRun, RunStatus
from doge.core.domain.evidence_models import EvidenceRecord
from doge.core.domain.model_policy import ModelPolicy
from doge.core.ports.enterprise_auth import AuthenticatedPrincipal
from doge.infrastructure.database.enterprise_governance import SQLiteEnterpriseGovernanceRepository
from doge.interfaces.api import deps
from doge.interfaces.api.middleware.tenant_context import TenantContextMiddleware
from doge.interfaces.api.routers.v1 import runs


def test_run_summary_api_is_feature_flagged():
    app = _app(feature_enabled=False)

    with TestClient(app) as client:
        response = client.get("/v1/runs/run-1/summary")

    assert response.status_code == 404
    assert response.json()["detail"] == "run summary API disabled"


def test_run_summary_api_returns_structured_resources():
    app = _app(feature_enabled=True)

    with TestClient(app) as client:
        summary = client.get("/v1/runs/run-1/summary")
        claims = client.get("/v1/runs/run-1/claims")
        citations = client.get("/v1/runs/run-1/citations")
        evaluation = client.get("/v1/runs/run-1/eval")

    assert summary.status_code == 200
    assert summary.json()["summary"]["status"] == "current"
    assert claims.json()["claims"][0]["claim_id"] == "claim-1"
    assert citations.json()["citations"][0]["document_id"] == "doc-allowed"
    assert evaluation.json()["eval"]["coverage_ratio"] == 1.0


def test_enterprise_run_citations_redact_denied_document_snippets(tmp_path):
    governance = SQLiteEnterpriseGovernanceRepository(tmp_path / "agent.db")
    app = _app(feature_enabled=True, governance=governance, enterprise=True)

    with TestClient(app) as client:
        response = client.get("/v1/runs/run-1/citations", headers={"Authorization": "Bearer token"})
        evaluation = client.get("/v1/runs/run-1/eval", headers={"Authorization": "Bearer token"})

    assert response.status_code == 200
    citation = response.json()["citations"][0]
    assert citation["document_id"] == "doc-allowed"
    assert citation["accessible"] is False
    assert citation["snippet"] == ""
    assert "inaccessible_citations" in evaluation.json()["eval"]["failed_checks"]


def _app(
    *,
    feature_enabled: bool,
    governance: SQLiteEnterpriseGovernanceRepository | None = None,
    enterprise: bool = False,
) -> FastAPI:
    app = FastAPI()
    if enterprise:
        app.add_middleware(
            TenantContextMiddleware,
            local_demo=False,
            auth_provider=_Provider(),
        )
    app.include_router(runs.router, prefix="/v1")
    runtime = _Runtime()
    evidence = _EvidenceRepo()
    app.dependency_overrides[deps.get_settings_dep] = lambda: Settings(
        features=FeatureConfig(run_summary_api=feature_enabled)
    )
    app.dependency_overrides[deps.get_persisted_research_agent_runtime] = lambda: runtime
    app.dependency_overrides[deps.get_agent_evidence_repository] = lambda: evidence
    app.dependency_overrides[deps.get_run_summary_use_case] = lambda: BuildRunSummary(runtime, evidence)
    if governance is not None:
        app.dependency_overrides[deps.get_enterprise_governance_repository] = lambda: governance
    return app


class _Provider:
    def authenticate_bearer(self, token: str) -> AuthenticatedPrincipal:
        return AuthenticatedPrincipal(subject_hash="user-a", tenant_id="tenant-a", roles=("analyst",))


class _Runtime:
    def __init__(self):
        self.run = AgentRun.create(
            workflow="investment_research",
            question="Analyze",
            run_id="run-1",
            model_policy=ModelPolicy(tenant_id="tenant-a", user_hash="user-a"),
        )
        self.run.status = RunStatus.COMPLETED
        self.artifact = AgentArtifact(
            artifact_id="art-1",
            run_id="run-1",
            kind="report",
            title="Report",
            content="Revenue grew 12%.",
            data={"claims": [{"claim_id": "claim-1", "text": "Revenue grew 12%.", "status": "supported"}]},
        )

    def get_run(self, run_id):
        return self.run if run_id == "run-1" else None

    def list_events(self, run_id):
        return []

    def list_artifacts(self, run_id):
        return [self.artifact] if run_id == "run-1" else []


class _EvidenceRepo:
    def __init__(self):
        self.evidence = EvidenceRecord(
            evidence_id="evd-1",
            run_id="run-1",
            document_id="doc-allowed",
            page_id="page-1",
            chunk_id="chunk-1",
            page_number=1,
            claim="Revenue grew 12%.",
            support_snippet="The filing says revenue grew 12%.",
        )

    def list_evidence(self, *, run_id=None, document_id=None, limit=20, tenant_id=None):
        if tenant_id not in (None, "tenant-a"):
            return []
        return [self.evidence]

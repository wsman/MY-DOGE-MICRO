from pathlib import Path

import pytest

from doge.core.domain.platform_models import Project, ResearchCase, Workspace
from doge.infrastructure.database.enterprise_governance import SQLiteEnterpriseGovernanceRepository
from doge.infrastructure.database.platform_repository import SQLitePlatformRepository
from doge.platform.workspace.application import (
    CaseAssetCreate,
    CaseAssetService,
    CaseDecisionCreate,
    CaseDecisionService,
    CaseExecutionService,
    PlatformAccessService,
    PlatformNotFoundError,
    PlatformRequestContext,
    PlatformValidationError,
)
from doge.shared.scope import TenantScope


def test_workspace_service_facade_is_thin_compatibility_wrapper():
    source = Path("src/doge/platform/workspace/service.py").read_text(encoding="utf-8")

    assert "class WorkspaceService" not in source
    assert "class ResearchCaseService" not in source
    assert "from doge.platform.workspace.application.case_service import" in source


def test_workspace_application_modules_export_compatible_services():
    from doge.platform.workspace import service as facade
    from doge.platform.workspace.application import (
        CaseAssetService,
        CaseDecisionService,
        CaseExecutionService,
        ProjectService,
        ResearchCaseService,
        WorkflowService,
        WorkspaceService,
    )

    assert facade.WorkspaceService is WorkspaceService
    assert facade.ProjectService is ProjectService
    assert facade.ResearchCaseService is ResearchCaseService
    assert facade.WorkflowService is WorkflowService
    assert not issubclass(CaseAssetService, ResearchCaseService)
    assert not issubclass(CaseDecisionService, ResearchCaseService)
    assert issubclass(CaseExecutionService, ResearchCaseService)


def test_focused_case_service_entries_expose_expected_behavior_names():
    from doge.platform.workspace.application import CaseAssetService, CaseDecisionService, CaseExecutionService

    assert hasattr(CaseAssetService, "add_case_asset")
    assert hasattr(CaseAssetService, "list_case_assets")
    assert hasattr(CaseDecisionService, "record_decision")
    assert hasattr(CaseDecisionService, "list_case_decisions")
    assert hasattr(CaseExecutionService, "execute_template")
    assert hasattr(CaseExecutionService, "preflight_template_execution")
    assert "add_case_asset" in CaseAssetService.__dict__
    assert "record_decision" in CaseDecisionService.__dict__


def test_case_asset_service_owns_validation_and_persistence(tmp_path):
    repo, case_id = _case_repo(tmp_path)
    documents = _DocumentRepo({"doc-1"})
    service = CaseAssetService(
        repo,
        PlatformAccessService(SQLiteEnterpriseGovernanceRepository(tmp_path / "agent.db")),
        document_repository=documents,
    )
    context = PlatformRequestContext()

    link = service.add_case_asset(
        context,
        case_id,
        CaseAssetCreate(asset_type="document", asset_id="doc-1", asset_name="10-K"),
    )

    assert link.asset_type == "document"
    assert documents.last_scope == TenantScope.local()
    assert [item.asset_link_id for item in service.list_case_assets(context, case_id)] == [link.asset_link_id]

    with pytest.raises(PlatformValidationError, match="unsupported asset_type"):
        service.add_case_asset(context, case_id, CaseAssetCreate(asset_type="chart", asset_id="doc-1"))

    with pytest.raises(PlatformNotFoundError, match="document not found"):
        service.add_case_asset(context, case_id, CaseAssetCreate(asset_type="document", asset_id="missing"))


def test_case_decision_service_owns_decision_persistence(tmp_path):
    repo, case_id = _case_repo(tmp_path)
    service = CaseDecisionService(
        repo,
        PlatformAccessService(SQLiteEnterpriseGovernanceRepository(tmp_path / "agent.db")),
    )
    context = PlatformRequestContext()

    decision = service.record_decision(
        context,
        case_id,
        CaseDecisionCreate(
            decision_type="hold",
            rationale="Need a second source.",
            source_run_ids=["run-1"],
            source_execution_ids=["exec-1"],
        ),
    )

    assert decision.actor_hash == "local-user"
    assert decision.source_run_ids == ["run-1"]
    assert decision.source_execution_ids == ["exec-1"]
    assert [item.decision_id for item in service.list_case_decisions(context, case_id)] == [decision.decision_id]

    with pytest.raises(PlatformValidationError, match="unsupported decision_type"):
        service.record_decision(context, case_id, CaseDecisionCreate(decision_type="maybe"))


def _case_repo(tmp_path):
    repo = SQLitePlatformRepository(tmp_path / "agent.db")
    workspace = Workspace.create(name="Workspace")
    project = Project.create(workspace_id=workspace.workspace_id, name="Project")
    research_case = ResearchCase.create(project_id=project.project_id, title="Case")
    repo.save_workspace(workspace)
    repo.save_project(project)
    repo.save_case(research_case)
    return repo, research_case.case_id


class _DocumentRepo:
    def __init__(self, document_ids):
        self._document_ids = set(document_ids)
        self.last_scope = None

    def get(self, document_id, scope=None, *, tenant_id=None):
        self.last_scope = scope
        if document_id in self._document_ids:
            return {"document_id": document_id}
        return None

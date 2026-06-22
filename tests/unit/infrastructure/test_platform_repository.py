from doge.core.domain.platform_models import Project, ResearchCase, WorkflowTemplate, Workspace
from doge.infrastructure.database.platform_repository import SQLitePlatformRepository


def test_platform_repository_persists_object_hierarchy_and_idempotent_run_links(tmp_path):
    repo = SQLitePlatformRepository(tmp_path / "agent.db")
    workspace = Workspace.create(name="Local Research", tenant_id="tenant-a")
    repo.save_workspace(workspace)
    project = Project.create(workspace_id=workspace.workspace_id, name="Semis", tenant_id="tenant-a")
    repo.save_project(project)
    case = ResearchCase.create(project_id=project.project_id, title="NVDA diligence", tenant_id="tenant-a")
    repo.save_case(case)

    first = repo.link_case_run(case_id=case.case_id, run_id="run-1", tenant_id="tenant-a")
    second = repo.link_case_run(case_id=case.case_id, run_id="run-1", tenant_id="tenant-a")

    assert repo.get_workspace(workspace.workspace_id, tenant_id="tenant-a") == workspace
    assert repo.list_projects(workspace_id=workspace.workspace_id, tenant_id="tenant-a") == [project]
    assert repo.list_cases(project_id=project.project_id, tenant_id="tenant-a") == [case]
    assert first.case_id == second.case_id == case.case_id
    assert first.run_id == second.run_id == "run-1"


def test_platform_repository_persists_workflow_templates(tmp_path):
    repo = SQLitePlatformRepository(tmp_path / "agent.db")
    template = WorkflowTemplate.create(slug="stock-diligence", name="Stock diligence", tenant_id="tenant-a")
    repo.save_workflow_template(template)

    assert repo.get_workflow_template(template.template_id, tenant_id="tenant-a") == template
    assert repo.get_workflow_template("stock-diligence", tenant_id="tenant-a") == template
    assert repo.list_workflow_templates(tenant_id="tenant-a") == [template]


def test_platform_repository_persists_template_run_links_idempotently(tmp_path):
    repo = SQLitePlatformRepository(tmp_path / "agent.db")
    template = WorkflowTemplate.create(slug="earnings-review", name="Earnings review", tenant_id="tenant-a")
    repo.save_workflow_template(template)

    first = repo.link_workflow_template_run(
        template_id=template.template_id,
        run_id="run-1",
        tenant_id="tenant-a",
    )
    second = repo.link_workflow_template_run(
        template_id=template.template_id,
        run_id="run-1",
        tenant_id="tenant-a",
    )

    assert first.template_id == second.template_id == template.template_id
    assert first.run_id == second.run_id == "run-1"
    assert first.tenant_id == second.tenant_id == "tenant-a"

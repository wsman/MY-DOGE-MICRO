from doge.infrastructure.database.platform_repository import SQLitePlatformRepository
from doge.platform.workspace.template_seed import BUILTIN_TEMPLATES, seed_workflow_templates


def test_seed_workflow_templates_dry_run_does_not_write(tmp_path):
    repo = SQLitePlatformRepository(tmp_path / "agent.db")

    result = seed_workflow_templates(repo, dry_run=True)

    assert result.dry_run is True
    assert set(result.inserted) == {item["slug"] for item in BUILTIN_TEMPLATES}
    assert repo.list_workflow_templates() == []


def test_seed_workflow_templates_is_idempotent_by_slug(tmp_path):
    repo = SQLitePlatformRepository(tmp_path / "agent.db")

    first = seed_workflow_templates(repo)
    second = seed_workflow_templates(repo)

    assert len(first.inserted) == len(BUILTIN_TEMPLATES)
    assert second.inserted == []
    assert set(second.existing) == {item["slug"] for item in BUILTIN_TEMPLATES}
    templates = repo.list_workflow_templates(limit=20)
    assert len(templates) == len(BUILTIN_TEMPLATES)
    earnings = repo.get_workflow_template("earnings_review")
    assert earnings is not None
    assert earnings.metadata["contract"]["approval_policy"]["publish"] == "required"

from doge.bootstrap.runtime_factories import slots as slots_module
from doge.bootstrap.workspace import WorkspaceContainer
from doge.config import reset_settings
from doge.infrastructure.database.platform_repository import SQLitePlatformRepository
from doge.platform.workspace.template_seed import BUILTIN_TEMPLATES, seed_workflow_templates

_FEATURE_VARS = [
    "DOGE_FEATURE_RUN_SUMMARY_API",
    "DOGE_FEATURE_PLATFORM_OBJECTS",
    "DOGE_FEATURE_WORKFLOW_TEMPLATES",
    "DOGE_FEATURE_CAPABILITY_REGISTRY",
    "DOGE_FEATURE_RUNTIME_OUTBOX_PUBLISHER",
    "DOGE_FEATURE_PYTHON_ANALYSIS_ENABLED",
    "DOGE_FEATURE_SLOT_PLATFORM",
    "DOGE_FEATURE_SLOT_GOVERNANCE",
    "DOGE_FEATURE_SLOT_WATCHER",
    "DOGE_FEATURE_SLOT_UI",
    "DOGE_FEATURE_SLOT_ENFORCEMENT",
    "DOGE_FEATURE_SLOT_LOADER",
    "DOGE_FEATURE_SLOT_INSTALL",
]


def _strip_feature_env(monkeypatch) -> None:
    for var in _FEATURE_VARS:
        monkeypatch.delenv(var, raising=False)


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


def test_seed_workflow_templates_includes_risk_alert_and_portfolio_impact_note(tmp_path):
    repo = SQLitePlatformRepository(tmp_path / "agent.db")

    seed_workflow_templates(repo)

    risk_alert = repo.get_workflow_template("risk_alert")
    portfolio_note = repo.get_workflow_template("portfolio_impact_note")
    slugs = {template.slug for template in repo.list_workflow_templates(limit=20)}
    assert risk_alert is not None
    assert risk_alert.output_contract["sections"] == [
        "risk_signal",
        "affected_exposure",
        "evidence",
        "action_candidates",
    ]
    assert risk_alert.metadata["contract"]["approval_policy"]["trade_action"] == "required"
    assert portfolio_note is not None
    assert portfolio_note.output_contract["sections"] == [
        "event_summary",
        "portfolio_exposure",
        "impact_assessment",
        "ic_questions",
    ]
    assert portfolio_note.metadata["contract"]["ui_schema"]["layout"] == "portfolio-impact-note"
    assert {"risk_alert", "portfolio_impact_note"}.issubset(slugs)


def test_seed_workflow_templates_accepts_injected_template_definitions(tmp_path):
    repo = SQLitePlatformRepository(tmp_path / "agent.db")
    templates = [
        {
            "slug": "custom_workflow",
            "name": "Custom Workflow",
            "description": "Injected by the caller.",
            "input_schema": {"required": ["topic"]},
            "run_instructions": "Use the injected template.",
            "tool_policy": {"model_policy": {"execution_profile": "financial_research"}},
            "evidence_policy": {"material_claims_require_citation": True},
            "output_contract": {"sections": ["summary"]},
            "metadata": {"contract": {"required_capabilities": ["feature.workflow_templates"]}},
        }
    ]

    result = seed_workflow_templates(repo, templates=templates)

    assert result.inserted == ["custom_workflow"]
    template = repo.get_workflow_template("custom_workflow")
    assert template is not None
    assert template.run_instructions == "Use the injected template."
    assert template.output_contract == {"sections": ["summary"]}


def test_workspace_container_uses_legacy_templates_when_slot_flag_off(tmp_path, monkeypatch):
    _strip_feature_env(monkeypatch)
    monkeypatch.setenv("DOGE_FEATURE_WORKFLOW_TEMPLATES", "1")
    reset_settings()

    templates = WorkspaceContainer(
        tmp_path / "agent.db"
    ).build_workflow_template_definitions()

    assert templates == tuple(BUILTIN_TEMPLATES)


def test_workspace_container_uses_slot_templates_when_both_flags_on(tmp_path, monkeypatch):
    _strip_feature_env(monkeypatch)
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    monkeypatch.setenv("DOGE_FEATURE_WORKFLOW_TEMPLATES", "1")
    reset_settings()
    sentinel = (
        {
            "slug": "slot_seeded",
            "name": "Slot Seeded",
            "input_schema": {},
            "run_instructions": "from slot",
            "tool_policy": {},
            "evidence_policy": {},
            "output_contract": {},
            "metadata": {},
        },
    )
    monkeypatch.setattr(
        slots_module,
        "build_slot_aware_workflow_templates",
        lambda: sentinel,
    )

    templates = WorkspaceContainer(
        tmp_path / "agent.db"
    ).build_workflow_template_definitions()

    assert templates == sentinel

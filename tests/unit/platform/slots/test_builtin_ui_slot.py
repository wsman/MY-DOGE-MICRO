"""Built-in UI slot tests for Sprint 044."""

from __future__ import annotations

from doge.platform.slots import SlotContext, SlotType
from doge.platform.workspace.ui_slot import ResearchWorkspaceUISlot


def test_research_workspace_ui_slot_manifest() -> None:
    manifest = ResearchWorkspaceUISlot().manifest()

    assert manifest.id == "ui.research_workspace"
    assert manifest.type is SlotType.UI
    assert manifest.owner == "workspace-ui"
    assert manifest.feature_flags == ("slot_platform", "slot_ui")
    assert manifest.provides.capabilities == ("ui.panels", "ui.research_workspace")
    assert manifest.provides.metadata["workspace"] == "research_workspace"
    assert "conclusion_evidence_matrix" in manifest.provides.metadata["panel_ids"]
    assert manifest.permissions.risk_level == "low"


def test_research_workspace_ui_slot_contributes_panels() -> None:
    context = SlotContext(settings=object(), feature_flags={"slot_platform": True, "slot_ui": True})

    contribution = ResearchWorkspaceUISlot().resolve(context)

    assert contribution.slot_id == "ui.research_workspace"
    assert len(contribution.ui_panels) == 20
    ids = {panel.panel_id for panel in contribution.ui_panels}
    assert {
        "guided_flow",
        "scenario_picker",
        "conclusion_evidence_matrix",
        "run_comparison_panel",
        "agent_timeline",
    } <= ids
    timeline = next(panel for panel in contribution.ui_panels if panel.panel_id == "agent_timeline")
    assert timeline.workspace == "research_workspace"
    assert timeline.zone == "research.timeline"
    assert timeline.modes == ("developer",)

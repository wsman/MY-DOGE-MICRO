"""Built-in UI slot for ResearchAgent workspace panel metadata."""

from __future__ import annotations

from doge.platform.slots import (
    SCHEMA_VERSION,
    ISlot,
    SlotCompatibility,
    SlotContribution,
    SlotContext,
    SlotHealth,
    SlotManifest,
    SlotPermissions,
    SlotProvides,
    SlotType,
    UIPanelContribution,
)

_WORKSPACE = "research_workspace"
_PANEL_IDS = (
    "guided_flow",
    "scenario_picker",
    "market_selector",
    "execution_profile_selector",
    "research_question",
    "run_preflight_checklist",
    "run_action",
    "document_uploader",
    "document_selector",
    "portfolio_importer",
    "memo_body",
    "empty_state_ctas",
    "status_row",
    "conclusion_evidence_matrix",
    "citation_drilldown",
    "approval_list",
    "maturity_panel",
    "run_comparison_panel",
    "cost_eval_panel",
    "agent_timeline",
)

_MANIFEST = SlotManifest(
    schema_version=SCHEMA_VERSION,
    id="ui.research_workspace",
    name="Research Workspace UI Panels",
    version="1.0.0",
    type=SlotType.UI,
    owner="workspace-ui",
    maturity="experimental",
    description="Provides ResearchAgent workspace panel metadata for slot-driven rendering.",
    entrypoint="doge.platform.workspace.ui_slot.ResearchWorkspaceUISlot",
    provides=SlotProvides(
        capabilities=("ui.panels", "ui.research_workspace"),
        metadata={
            "workspace": _WORKSPACE,
            "panel_ids": _PANEL_IDS,
        },
    ),
    permissions=SlotPermissions(network="none", risk_level="low"),
    health=SlotHealth(status="experimental"),
    feature_flags=("slot_platform", "slot_ui"),
    compatibility=SlotCompatibility(runtime_min="1"),
)


class ResearchWorkspaceUISlot(ISlot):
    """Built-in UI slot wrapping the current ResearchAgentView panel layout."""

    def manifest(self) -> SlotManifest:
        return _MANIFEST

    def resolve(self, context: SlotContext) -> SlotContribution:
        return SlotContribution(
            slot_id="ui.research_workspace",
            ui_panels=_research_panels(),
        )


def _research_panels() -> tuple[UIPanelContribution, ...]:
    modes = ("analyst", "developer")
    developer = ("developer",)
    return (
        UIPanelContribution(
            "guided_flow",
            "research.input",
            "components/agent/GuidedFlow.vue",
            order=10,
            modes=modes,
            label="Guided Flow",
            workspace=_WORKSPACE,
        ),
        UIPanelContribution(
            "scenario_picker",
            "research.input",
            "components/agent/ScenarioPicker.vue",
            order=20,
            modes=modes,
            label="Scenario Picker",
            workspace=_WORKSPACE,
        ),
        UIPanelContribution(
            "market_selector",
            "research.input",
            "builtin:market_selector",
            order=30,
            modes=modes,
            label="Market Selector",
            workspace=_WORKSPACE,
        ),
        UIPanelContribution(
            "execution_profile_selector",
            "research.input",
            "components/agent/ExecutionProfileSelector.vue",
            order=40,
            modes=modes,
            label="Execution Profile",
            workspace=_WORKSPACE,
        ),
        UIPanelContribution(
            "research_question",
            "research.input",
            "builtin:research_question",
            order=50,
            modes=modes,
            label="Research Question",
            workspace=_WORKSPACE,
        ),
        UIPanelContribution(
            "run_preflight_checklist",
            "research.input",
            "components/agent/RunPreflightChecklist.vue",
            order=60,
            modes=modes,
            label="Run Preflight",
            workspace=_WORKSPACE,
        ),
        UIPanelContribution(
            "run_action",
            "research.input",
            "builtin:run_action",
            order=70,
            modes=modes,
            label="Run Action",
            workspace=_WORKSPACE,
        ),
        UIPanelContribution(
            "document_uploader",
            "research.input",
            "components/agent/DocumentUploader.vue",
            order=80,
            modes=modes,
            label="Document Uploader",
            workspace=_WORKSPACE,
        ),
        UIPanelContribution(
            "document_selector",
            "research.input",
            "components/agent/DocumentSelector.vue",
            order=90,
            modes=modes,
            label="Document Selector",
            workspace=_WORKSPACE,
        ),
        UIPanelContribution(
            "portfolio_importer",
            "research.input",
            "components/agent/PortfolioImporter.vue",
            order=100,
            modes=modes,
            label="Portfolio Importer",
            workspace=_WORKSPACE,
        ),
        UIPanelContribution(
            "memo_body",
            "research.memo",
            "builtin:memo_body",
            order=10,
            modes=modes,
            label="Memo Body",
            workspace=_WORKSPACE,
        ),
        UIPanelContribution(
            "empty_state_ctas",
            "research.memo",
            "components/agent/EmptyStateCtas.vue",
            order=20,
            modes=modes,
            label="Empty State CTAs",
            workspace=_WORKSPACE,
        ),
        UIPanelContribution(
            "status_row",
            "research.evidence",
            "builtin:status_row",
            order=10,
            modes=modes,
            label="Status Row",
            workspace=_WORKSPACE,
        ),
        UIPanelContribution(
            "conclusion_evidence_matrix",
            "research.evidence",
            "components/agent/ConclusionEvidenceMatrix.vue",
            order=20,
            modes=modes,
            required_artifact_fields=("structured_claims",),
            label="Conclusion Evidence Matrix",
            workspace=_WORKSPACE,
        ),
        UIPanelContribution(
            "citation_drilldown",
            "research.evidence",
            "components/agent/CitationDrilldown.vue",
            order=30,
            modes=modes,
            required_artifact_fields=("citations",),
            label="Citation Drilldown",
            workspace=_WORKSPACE,
        ),
        UIPanelContribution(
            "approval_list",
            "research.evidence",
            "builtin:approval_list",
            order=40,
            modes=modes,
            label="Approval List",
            workspace=_WORKSPACE,
        ),
        UIPanelContribution(
            "maturity_panel",
            "research.quality",
            "components/common/MaturityPanel.vue",
            order=10,
            modes=modes,
            label="Maturity Panel",
            workspace=_WORKSPACE,
        ),
        UIPanelContribution(
            "run_comparison_panel",
            "research.quality",
            "components/agent/RunComparisonPanel.vue",
            order=20,
            modes=modes,
            label="Run Comparison",
            workspace=_WORKSPACE,
        ),
        UIPanelContribution(
            "cost_eval_panel",
            "research.quality",
            "components/agent/CostEvalPanel.vue",
            order=30,
            modes=developer,
            label="Cost / Eval",
            workspace=_WORKSPACE,
        ),
        UIPanelContribution(
            "agent_timeline",
            "research.timeline",
            "builtin:agent_timeline",
            order=10,
            modes=developer,
            label="Agent Timeline",
            workspace=_WORKSPACE,
        ),
    )

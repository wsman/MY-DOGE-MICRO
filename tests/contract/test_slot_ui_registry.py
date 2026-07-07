"""UI slot consumer parity tests (Sprint 044)."""

from __future__ import annotations

import pytest

from doge.bootstrap.runtime_factories import slots as slots_module
from doge.config import Settings
from doge.config.settings import FeatureConfig
from doge.platform.slots import (
    ISlot,
    SlotConfigurationError,
    SlotContribution,
    SlotContext,
    SlotHealth,
    SlotManifest,
    SlotProvides,
    SlotRegistry,
    SlotType,
    UIPanelContribution,
)


class _UISlot(ISlot):
    def __init__(self, slot_id: str, panel: UIPanelContribution) -> None:
        self._slot_id = slot_id
        self._panel = panel

    def manifest(self) -> SlotManifest:
        return SlotManifest(
            schema_version=1,
            id=self._slot_id,
            name="Test UI Slot",
            version="1.0.0",
            type=SlotType.UI,
            owner="slot-tests",
            maturity="experimental",
            description="Test UI panel slot.",
            entrypoint="tests.contract.test_slot_ui_registry.UISlot",
            provides=SlotProvides(capabilities=("ui.panels",)),
            health=SlotHealth(status="experimental"),
            feature_flags=("slot_platform", "slot_ui"),
        )

    def resolve(self, context: SlotContext) -> SlotContribution:
        return SlotContribution(
            slot_id=self._slot_id,
            ui_panels=(self._panel,),
        )


def test_ui_panel_registry_is_disabled_until_slot_ui_flag_is_on() -> None:
    platform_off = slots_module.build_slot_aware_ui_panels(
        settings=Settings(features=FeatureConfig(slot_platform=False, slot_ui=True))
    )
    ui_off = slots_module.build_slot_aware_ui_panels(
        settings=Settings(features=FeatureConfig(slot_platform=True, slot_ui=False))
    )

    assert platform_off is None
    assert ui_off is None


def test_ui_panel_registry_resolves_research_workspace_panels() -> None:
    registry = slots_module.build_slot_aware_ui_panels(
        settings=Settings(features=FeatureConfig(slot_platform=True, slot_ui=True))
    )

    assert registry is not None
    analyst_ids = [
        panel.panel_id
        for panel in registry.panels_for("research_workspace", mode="analyst")
    ]
    developer_ids = [
        panel.panel_id
        for panel in registry.panels_for("research_workspace", mode="developer")
    ]
    assert "guided_flow" in analyst_ids
    assert "cost_eval_panel" not in analyst_ids
    assert "agent_timeline" not in analyst_ids
    assert "cost_eval_panel" in developer_ids
    assert "agent_timeline" in developer_ids


def test_ui_panel_rows_serialize_for_api_consumers() -> None:
    rows = slots_module.build_slot_ui_panel_rows(
        Settings(features=FeatureConfig(slot_platform=True, slot_ui=True)),
        workspace="research_workspace",
        zone="research.evidence",
        mode="analyst",
    )

    assert [row["panel_id"] for row in rows] == [
        "status_row",
        "conclusion_evidence_matrix",
        "citation_drilldown",
        "approval_list",
    ]
    matrix = next(row for row in rows if row["panel_id"] == "conclusion_evidence_matrix")
    assert matrix["workspace"] == "research_workspace"
    assert matrix["required_artifact_fields"] == ["structured_claims"]


def test_duplicate_ui_panel_ids_fail_fast(monkeypatch) -> None:
    registry = SlotRegistry()
    registry.register(_UISlot("ui.one", UIPanelContribution("same", "research.input", "One.vue")))
    registry.register(_UISlot("ui.two", UIPanelContribution("same", "research.input", "Two.vue")))
    monkeypatch.setattr(slots_module, "build_builtin_slot_registry", lambda: registry)

    with pytest.raises(SlotConfigurationError, match="duplicate UI panel"):
        slots_module.build_slot_aware_ui_panels(
            settings=Settings(features=FeatureConfig(slot_platform=True, slot_ui=True))
        )

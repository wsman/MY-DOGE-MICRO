"""UI panel registry tests."""

from __future__ import annotations

import pytest

from doge.platform.slots import SlotConfigurationError, UIPanelContribution
from doge.platform.workspace.ui_panels import UIPanelRegistry


def test_ui_panel_registry_filters_and_orders_panels() -> None:
    registry = UIPanelRegistry(
        (
            UIPanelContribution("late", "research.input", "Late.vue", order=20),
            UIPanelContribution("early", "research.input", "Early.vue", order=10),
            UIPanelContribution(
                "dev",
                "research.quality",
                "Dev.vue",
                order=5,
                modes=("developer",),
            ),
            UIPanelContribution(
                "other",
                "research.input",
                "Other.vue",
                workspace="other_workspace",
            ),
        )
    )

    assert [panel.panel_id for panel in registry.panels_for("research_workspace")] == [
        "dev",
        "early",
        "late",
    ]
    assert [panel.panel_id for panel in registry.panels_for("research_workspace", zone="research.input")] == [
        "early",
        "late",
    ]
    assert [panel.panel_id for panel in registry.panels_for("research_workspace", mode="analyst")] == [
        "early",
        "late",
    ]
    assert [panel.panel_id for panel in registry.panels_for("research_workspace", mode="developer")] == [
        "dev",
        "early",
        "late",
    ]


def test_ui_panel_registry_rejects_duplicate_workspace_panel_ids() -> None:
    with pytest.raises(SlotConfigurationError, match="duplicate UI panel"):
        UIPanelRegistry(
            (
                UIPanelContribution("same", "research.input", "One.vue"),
                UIPanelContribution("same", "research.evidence", "Two.vue"),
            )
        )


def test_ui_panel_registry_serializes_rows() -> None:
    registry = UIPanelRegistry(
        (
            UIPanelContribution(
                "matrix",
                "research.evidence",
                "Matrix.vue",
                required_artifact_fields=("structured_claims",),
                label="Matrix",
            ),
        )
    )

    assert registry.rows(workspace="research_workspace") == (
        {
            "panel_id": "matrix",
            "zone": "research.evidence",
            "component_module": "Matrix.vue",
            "order": 0,
            "modes": [],
            "required_artifact_fields": ["structured_claims"],
            "label": "Matrix",
            "workspace": "research_workspace",
        },
    )

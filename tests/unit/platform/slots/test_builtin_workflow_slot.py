"""Built-in workflow slot tests for Sprint 035."""

from __future__ import annotations

from doge.platform.slots import SlotContext, SlotType
from doge.platform.workspace.slot import WorkflowTemplatesSlot
from doge.platform.workspace.template_seed import BUILTIN_TEMPLATES


def test_workflow_templates_slot_manifest() -> None:
    manifest = WorkflowTemplatesSlot().manifest()

    assert manifest.id == "workflow.templates"
    assert manifest.type is SlotType.WORKFLOW
    assert manifest.owner == "workspace-workflow"
    assert manifest.feature_flags == ("slot_platform", "workflow_templates")
    assert manifest.provides.metadata["template_slugs"] == tuple(
        item["slug"] for item in BUILTIN_TEMPLATES
    )


def test_workflow_templates_slot_contributes_template_factories() -> None:
    slot = WorkflowTemplatesSlot()
    context = SlotContext(
        settings=object(),
        feature_flags={"slot_platform": True, "workflow_templates": True},
    )

    contribution = slot.resolve(context)
    workflows = contribution.workflows

    assert contribution.slot_id == "workflow.templates"
    assert [workflow.slug for workflow in workflows] == [
        item["slug"] for item in BUILTIN_TEMPLATES
    ]
    assert workflows[0].capabilities == ("feature.workflow_templates",)
    assert workflows[0].template_factory(context) == BUILTIN_TEMPLATES[0]


def test_workflow_template_factory_returns_defensive_copy() -> None:
    context = SlotContext(
        settings=object(),
        feature_flags={"slot_platform": True, "workflow_templates": True},
    )
    workflow = WorkflowTemplatesSlot().resolve(context).workflows[0]

    first = workflow.template_factory(context)
    first["metadata"]["contract"]["approval_policy"]["publish"] = "mutated"
    second = workflow.template_factory(context)

    assert second["metadata"]["contract"]["approval_policy"]["publish"] == "optional"

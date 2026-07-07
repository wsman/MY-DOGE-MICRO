"""Built-in workflow slot for canonical workflow templates."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

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
    WorkflowTemplateContribution,
)
from doge.platform.workspace.template_seed import BUILTIN_TEMPLATES

_TEMPLATE_SLUGS = tuple(item["slug"] for item in BUILTIN_TEMPLATES)

_MANIFEST = SlotManifest(
    schema_version=SCHEMA_VERSION,
    id="workflow.templates",
    name="Workflow Templates",
    version="1.0.0",
    type=SlotType.WORKFLOW,
    owner="workspace-workflow",
    maturity="experimental",
    description=(
        "Provides the canonical built-in workflow templates used by the "
        "case-centered research workspace."
    ),
    entrypoint="doge.platform.workspace.slot.WorkflowTemplatesSlot",
    provides=SlotProvides(
        capabilities=("workflow_templates",),
        metadata={"template_slugs": _TEMPLATE_SLUGS},
    ),
    permissions=SlotPermissions(database="write", risk_level="low"),
    health=SlotHealth(status="experimental"),
    feature_flags=("slot_platform", "workflow_templates"),
    compatibility=SlotCompatibility(runtime_min="1"),
)


class WorkflowTemplatesSlot(ISlot):
    """Built-in workflow slot wrapping the canonical template definitions."""

    def manifest(self) -> SlotManifest:
        return _MANIFEST

    def resolve(self, context: SlotContext) -> SlotContribution:
        return SlotContribution(
            slot_id="workflow.templates",
            workflows=tuple(
                WorkflowTemplateContribution(
                    slug=item["slug"],
                    template_factory=_template_factory(item),
                    capabilities=("feature.workflow_templates",),
                )
                for item in BUILTIN_TEMPLATES
            ),
        )


def _template_factory(item: Mapping[str, Any]):
    template = deepcopy(dict(item))

    def factory(context: SlotContext) -> Mapping[str, Any]:
        return deepcopy(template)

    return factory

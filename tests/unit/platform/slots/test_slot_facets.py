"""SlotContribution facet representability tests."""

from __future__ import annotations

from typing import Any

import pytest

from doge.platform.slots import (
    DataSourceContribution,
    DocumentParserContribution,
    EvalSuiteContribution,
    GatewayRouteContribution,
    GovernancePolicyContribution,
    ISlot,
    ModelBackendContribution,
    SlotContribution,
    SlotContext,
    SlotHealth,
    SlotManifest,
    SlotProvides,
    SlotRegistry,
    SlotType,
    UIPanelContribution,
    WatcherContribution,
    WatcherDecision,
    WorkflowTemplateContribution,
)


class _FacetSlot(ISlot):
    def __init__(
        self,
        slot_type: SlotType,
        contribution: SlotContribution,
        *,
        slot_id: str = "facet.slot",
    ) -> None:
        self._manifest = SlotManifest(
            schema_version=1,
            id=slot_id,
            name="Facet Slot",
            version="1.0.0",
            type=slot_type,
            owner="slot-tests",
            maturity="experimental",
            description="Stub slot for facet contribution tests.",
            entrypoint="tests.unit.platform.slots.test_slot_facets.FacetSlot",
            provides=SlotProvides(capabilities=("facet.test",)),
            health=SlotHealth(status="experimental"),
            feature_flags=("slot_platform",),
        )
        self._contribution = contribution

    def manifest(self) -> SlotManifest:
        return self._manifest

    def resolve(self, context: SlotContext) -> SlotContribution:
        return self._contribution


def _context() -> SlotContext:
    return SlotContext(settings=object(), feature_flags={"slot_platform": True})


def _factory(_context: SlotContext) -> object:
    return object()


def _template(_context: SlotContext) -> dict[str, Any]:
    return {"slug": "workflow.test"}


def _watcher(_event: Any, _context: SlotContext) -> WatcherDecision:
    return WatcherDecision(action="allow")


@pytest.mark.parametrize(
    ("slot_type", "field_name", "facet"),
    [
        (
            SlotType.MODEL,
            "model_backends",
            ModelBackendContribution("backend.test", _factory),
        ),
        (
            SlotType.WORKFLOW,
            "workflows",
            WorkflowTemplateContribution("workflow.test", _template),
        ),
        (
            SlotType.DATA,
            "data_sources",
            DataSourceContribution("data.test", _factory, markets=("cn",)),
        ),
        (
            SlotType.DOCUMENT,
            "document_parsers",
            DocumentParserContribution("parser.test", _factory, (".md",)),
        ),
        (
            SlotType.GATEWAY,
            "routes",
            GatewayRouteContribution("route.test", _factory, prefix="/v1"),
        ),
        (
            SlotType.UI,
            "ui_panels",
            UIPanelContribution("panel.test", "research.evidence", "Panel.vue"),
        ),
        (
            SlotType.WATCHER,
            "watchers",
            WatcherContribution("watcher.test", _watcher),
        ),
        (
            SlotType.EVAL,
            "eval_suites",
            EvalSuiteContribution("eval.test", "tests/fixtures/eval.json"),
        ),
        (
            SlotType.GOVERNANCE,
            "governance_policies",
            GovernancePolicyContribution("policy.test", "approval_policy", {}),
        ),
    ],
)
def test_registry_resolves_each_non_tool_facet(slot_type, field_name, facet) -> None:
    contribution = SlotContribution("facet.slot", **{field_name: (facet,)})
    registry = SlotRegistry()
    registry.register(_FacetSlot(slot_type, contribution))

    resolved = registry.resolve_contributions(_context())

    assert len(resolved) == 1
    assert getattr(resolved[0], field_name) == (facet,)
    assert resolved[0].tools == ()
    assert resolved[0].executor is None


def test_contribution_can_carry_multiple_facets() -> None:
    model = ModelBackendContribution("backend.test", _factory)
    workflow = WorkflowTemplateContribution("workflow.test", _template)
    watcher = WatcherContribution("watcher.test", _watcher)

    contribution = SlotContribution(
        "multi.slot",
        model_backends=(model,),
        workflows=(workflow,),
        watchers=(watcher,),
    )

    assert contribution.model_backends == (model,)
    assert contribution.workflows == (workflow,)
    assert contribution.watchers == (watcher,)

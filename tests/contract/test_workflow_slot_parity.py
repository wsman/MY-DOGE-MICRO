"""Workflow-template slot parity tests for Sprint 035."""

from __future__ import annotations

import pytest

from doge.bootstrap.runtime_factories import slots as slots_module
from doge.config import reset_settings
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
    WorkflowTemplateContribution,
)
from doge.platform.workspace.template_seed import BUILTIN_TEMPLATES

_ALL_FEATURE_VARS = [
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


class _WorkflowSlot(ISlot):
    def __init__(self, slot_id: str, slug: str, template_slug: str | None = None) -> None:
        self._slot_id = slot_id
        self._slug = slug
        self._template_slug = template_slug or slug
        self._manifest = SlotManifest(
            schema_version=1,
            id=slot_id,
            name="Workflow Slot",
            version="1.0.0",
            type=SlotType.WORKFLOW,
            owner="slot-tests",
            maturity="experimental",
            description="Stub workflow slot.",
            entrypoint="tests.contract.test_workflow_slot_parity.WorkflowSlot",
            provides=SlotProvides(capabilities=("workflow_templates",)),
            health=SlotHealth(status="experimental"),
            feature_flags=("slot_platform", "workflow_templates"),
        )

    def manifest(self) -> SlotManifest:
        return self._manifest

    def resolve(self, context: SlotContext) -> SlotContribution:
        return SlotContribution(
            slot_id=self._slot_id,
            workflows=(
                WorkflowTemplateContribution(
                    self._slug,
                    lambda _ctx: {"slug": self._template_slug, "name": self._slug},
                ),
            ),
        )


def _strip_feature_env(monkeypatch, keep: set[str] | None = None) -> None:
    keep = keep or set()
    for var in _ALL_FEATURE_VARS:
        if var not in keep:
            monkeypatch.delenv(var, raising=False)


def test_slot_aware_workflow_templates_match_builtin_templates(monkeypatch) -> None:
    _strip_feature_env(
        monkeypatch,
        keep={"DOGE_FEATURE_SLOT_PLATFORM", "DOGE_FEATURE_WORKFLOW_TEMPLATES"},
    )
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    monkeypatch.setenv("DOGE_FEATURE_WORKFLOW_TEMPLATES", "1")
    reset_settings()

    templates = slots_module.build_slot_aware_workflow_templates()

    assert templates == tuple(BUILTIN_TEMPLATES)


def test_slot_aware_workflow_templates_require_workflow_flag(monkeypatch) -> None:
    _strip_feature_env(
        monkeypatch,
        keep={"DOGE_FEATURE_SLOT_PLATFORM", "DOGE_FEATURE_WORKFLOW_TEMPLATES"},
    )
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    monkeypatch.setenv("DOGE_FEATURE_WORKFLOW_TEMPLATES", "0")
    reset_settings()

    assert slots_module.build_slot_aware_workflow_templates() == ()


def test_duplicate_workflow_template_slugs_fail_fast(monkeypatch) -> None:
    registry = SlotRegistry()
    registry.register(_WorkflowSlot("workflow.one", "duplicate"))
    registry.register(_WorkflowSlot("workflow.two", "duplicate"))
    monkeypatch.setattr(slots_module, "build_builtin_slot_registry", lambda: registry)
    _strip_feature_env(
        monkeypatch,
        keep={"DOGE_FEATURE_SLOT_PLATFORM", "DOGE_FEATURE_WORKFLOW_TEMPLATES"},
    )
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    monkeypatch.setenv("DOGE_FEATURE_WORKFLOW_TEMPLATES", "1")
    reset_settings()

    with pytest.raises(SlotConfigurationError, match="duplicate"):
        slots_module.build_slot_aware_workflow_templates()


def test_workflow_template_slug_mismatch_fails_fast(monkeypatch) -> None:
    registry = SlotRegistry()
    registry.register(_WorkflowSlot("workflow.bad", "declared", template_slug="actual"))
    monkeypatch.setattr(slots_module, "build_builtin_slot_registry", lambda: registry)
    _strip_feature_env(
        monkeypatch,
        keep={"DOGE_FEATURE_SLOT_PLATFORM", "DOGE_FEATURE_WORKFLOW_TEMPLATES"},
    )
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    monkeypatch.setenv("DOGE_FEATURE_WORKFLOW_TEMPLATES", "1")
    reset_settings()

    with pytest.raises(SlotConfigurationError, match="mismatched"):
        slots_module.build_slot_aware_workflow_templates()

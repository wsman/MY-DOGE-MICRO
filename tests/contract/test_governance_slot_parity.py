"""Governance slot consumer parity and composition tests (Sprint 037)."""

from __future__ import annotations

import pytest

from doge.application.agent.tool_service import ToolApplicationService
from doge.application.tools import factory as tool_factory
from doge.bootstrap.runtime_factories import slots as slots_module
from doge.config import reset_settings
from doge.core.domain.tool_policy import ToolCategory
from doge.platform.slots import (
    GovernancePolicyContribution,
    ISlot,
    SlotConfigurationError,
    SlotContribution,
    SlotContext,
    SlotHealth,
    SlotManifest,
    SlotProvides,
    SlotRegistry,
    SlotType,
)

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


class _FakeGatewayContainer:
    def __init__(self, service: ToolApplicationService) -> None:
        self._service = service

    def build_tool_application_service(self) -> ToolApplicationService:
        return self._service


class _GovernancePolicySlot(ISlot):
    def __init__(
        self,
        slot_id: str,
        *,
        policy_id: str,
        checker_factory,
    ) -> None:
        self._slot_id = slot_id
        self._policy_id = policy_id
        self._checker_factory = checker_factory

    def manifest(self) -> SlotManifest:
        return SlotManifest(
            schema_version=1,
            id=self._slot_id,
            name="Test Governance Slot",
            version="1.0.0",
            type=SlotType.GOVERNANCE,
            owner="slot-tests",
            maturity="experimental",
            description="Test governance policy slot.",
            entrypoint="tests.contract.test_governance_slot_parity.GovernancePolicySlot",
            provides=SlotProvides(capabilities=("tool_entitlement",)),
            health=SlotHealth(status="experimental"),
            feature_flags=("slot_platform", "slot_governance"),
        )

    def resolve(self, context: SlotContext) -> SlotContribution:
        return SlotContribution(
            slot_id=self._slot_id,
            governance_policies=(
                GovernancePolicyContribution(
                    policy_id=self._policy_id,
                    kind="tool_entitlement",
                    payload={},
                    entitlement_checker_factory=self._checker_factory,
                ),
            ),
        )


def _strip_feature_env(monkeypatch, keep: set[str] | None = None) -> None:
    keep = keep or set()
    for var in _ALL_FEATURE_VARS:
        if var not in keep:
            monkeypatch.delenv(var, raising=False)


def _schemas(registry) -> list[dict]:
    return sorted(registry.schemas_for_context(), key=lambda s: s["function"]["name"])


def _records(registry) -> list[dict]:
    return sorted(registry.capability_records_for_context(), key=lambda r: r["name"])


def test_default_governance_slot_keeps_tool_registry_equivalent(monkeypatch) -> None:
    service = ToolApplicationService()

    _strip_feature_env(
        monkeypatch,
        keep={"DOGE_FEATURE_SLOT_PLATFORM", "DOGE_FEATURE_SLOT_GOVERNANCE"},
    )
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    monkeypatch.setenv("DOGE_FEATURE_SLOT_GOVERNANCE", "1")
    reset_settings()
    registry_on = slots_module.build_slot_aware_tool_registry(lambda: _FakeGatewayContainer(service))

    _strip_feature_env(monkeypatch)
    reset_settings()
    registry_off = tool_factory.build_default_tool_registry(service=service)

    assert _schemas(registry_on) == _schemas(registry_off)
    assert _records(registry_on) == _records(registry_off)
    assert registry_on.execute("publish_investment_memo", {"memo_id": "memo-1"}).data[
        "approval_required"
    ] is True


def test_governance_policy_can_constrain_tool_registry(monkeypatch) -> None:
    service = ToolApplicationService()
    registry = SlotRegistry()
    registry.register(
        _GovernancePolicySlot(
            "governance.read_only_only",
            policy_id="governance.read_only_only",
            checker_factory=lambda _context: _OnlyReadOnlyChecker(),
        )
    )
    monkeypatch.setattr(slots_module, "build_builtin_slot_registry", lambda: registry)
    _strip_feature_env(
        monkeypatch,
        keep={"DOGE_FEATURE_SLOT_PLATFORM", "DOGE_FEATURE_SLOT_GOVERNANCE"},
    )
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    monkeypatch.setenv("DOGE_FEATURE_SLOT_GOVERNANCE", "1")
    reset_settings()

    tool_registry = slots_module.build_slot_aware_tool_registry(lambda: _FakeGatewayContainer(service))
    schema_names = {schema["function"]["name"] for schema in tool_registry.schemas_for_context()}

    assert "query_stock" in schema_names
    assert "publish_investment_memo" not in schema_names
    denied = tool_registry.execute("publish_investment_memo", {"memo_id": "memo-1"})
    assert denied.ok is False
    assert denied.error == "tool not permitted"


def test_duplicate_governance_policy_fails_fast(monkeypatch) -> None:
    registry = SlotRegistry()
    registry.register(
        _GovernancePolicySlot(
            "governance.one",
            policy_id="governance.duplicate",
            checker_factory=lambda _context: _OnlyReadOnlyChecker(),
        )
    )
    registry.register(
        _GovernancePolicySlot(
            "governance.two",
            policy_id="governance.duplicate",
            checker_factory=lambda _context: _OnlyReadOnlyChecker(),
        )
    )
    monkeypatch.setattr(slots_module, "build_builtin_slot_registry", lambda: registry)
    _strip_feature_env(
        monkeypatch,
        keep={"DOGE_FEATURE_SLOT_PLATFORM", "DOGE_FEATURE_SLOT_GOVERNANCE"},
    )
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    monkeypatch.setenv("DOGE_FEATURE_SLOT_GOVERNANCE", "1")
    reset_settings()

    try:
        with pytest.raises(SlotConfigurationError, match="duplicate governance policy"):
            slots_module.build_slot_aware_entitlement_checker()
    finally:
        reset_settings()


class _OnlyReadOnlyChecker:
    def can_execute(self, context, tool_name, category):
        return category == ToolCategory.READ_ONLY

    def requires_approval(self, context, tool_name, category):
        return category == ToolCategory.HIGH_RISK

    def redact_schema(self, context, schema, category):
        if not self.can_execute(context, schema.get("function", {}).get("name", ""), category):
            return None
        return schema

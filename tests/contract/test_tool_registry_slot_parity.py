"""Tool-registry slot parity: flag-off byte-identical, flag-on equivalent (ADR-0042).

The load-bearing safety guarantee for Sprint 033: enabling
``DOGE_FEATURE_SLOT_PLATFORM`` must not change the tool-registry payload or tool
execution versus the legacy factory path. This test builds the registry both
ways against the SAME ``ToolApplicationService`` instance and compares schemas,
capability records, and a representative execution smoke.

Isolation: this file lives in ``tests/contract/`` and has no
``tests/test_settings.py`` autouse fixture, so every case strips all
``DOGE_FEATURE_*`` env vars (except the one under test) and resets the settings
singleton before constructing a registry.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from doge.application.agent.tool_service import ToolApplicationService
from doge.application.tools import factory as tool_factory
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
)

_BASELINE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "slot_platform"
    / "baseline_v1_tools_flag_off.json"
)

_ALL_FEATURE_VARS = [
    "DOGE_FEATURE_RUN_SUMMARY_API",
    "DOGE_FEATURE_PLATFORM_OBJECTS",
    "DOGE_FEATURE_WORKFLOW_TEMPLATES",
    "DOGE_FEATURE_CAPABILITY_REGISTRY",
    "DOGE_FEATURE_RUNTIME_OUTBOX_PUBLISHER",
    "DOGE_FEATURE_PYTHON_ANALYSIS_ENABLED",
    "DOGE_FEATURE_SLOT_PLATFORM",
]


class _FakeGatewayContainer:
    """Minimal gateway-container callable returning a fixed service."""

    def __init__(self, service: ToolApplicationService) -> None:
        self._service = service

    def build_tool_application_service(self) -> ToolApplicationService:
        return self._service


class _BadToolSlot(ISlot):
    def manifest(self) -> SlotManifest:
        return SlotManifest(
            schema_version=1,
            id="tool.bad",
            name="Bad Tool Slot",
            version="1.0.0",
            type=SlotType.TOOL,
            owner="slot-tests",
            maturity="experimental",
            description="Stub tool slot missing an executor.",
            entrypoint="tests.contract.test_tool_registry_slot_parity.BadToolSlot",
            provides=SlotProvides(tools=("query_stock",)),
            health=SlotHealth(status="experimental"),
            feature_flags=("slot_platform",),
        )

    def resolve(self, context: SlotContext) -> SlotContribution:
        service = context.tool_application_service
        descriptor = service.tool_descriptors()[0]
        return SlotContribution(slot_id="tool.bad", tools=(descriptor,))


@pytest.fixture
def service() -> ToolApplicationService:
    return ToolApplicationService()


def _strip_feature_env(monkeypatch, keep: set[str] | None = None) -> None:
    keep = keep or set()
    for var in _ALL_FEATURE_VARS:
        if var not in keep:
            monkeypatch.delenv(var, raising=False)


def _flag_off_registry(service: ToolApplicationService) -> "object":
    reset_settings()
    return tool_factory.build_default_tool_registry(service=service)


def _flag_on_registry(service: ToolApplicationService) -> "object":
    reset_settings()
    return slots_module.build_slot_aware_tool_registry(lambda: _FakeGatewayContainer(service))


def _schemas(registry) -> list[dict]:
    return sorted(
        registry.schemas_for_context(), key=lambda s: s["function"]["name"]
    )


def _records(registry) -> list[dict]:
    return sorted(registry.capability_records_for_context(), key=lambda r: r["name"])


def test_v1_tools_payload_is_byte_identical_with_slots_off(monkeypatch, service) -> None:
    # Arrange — flag firmly off, settings singleton reset
    _strip_feature_env(monkeypatch)
    # Act
    registry = _flag_off_registry(service)
    # Assert — matches the frozen flag-off baseline
    baseline = json.loads(_BASELINE.read_text(encoding="utf-8"))
    assert len(registry.schemas) == baseline["count"] == 23
    assert _schemas(registry) == baseline["schemas"]
    assert _records(registry) == baseline["records"]


def test_v1_tools_payload_is_equivalent_with_slots_on(monkeypatch, service) -> None:
    # Arrange / Act — flag on vs flag off, both against the same service
    _strip_feature_env(monkeypatch, keep={"DOGE_FEATURE_SLOT_PLATFORM"})
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    registry_on = _flag_on_registry(service)

    _strip_feature_env(monkeypatch)
    registry_off = _flag_off_registry(service)

    # Assert — schema payload and capability records are equal, no double-registration
    assert _schemas(registry_on) == _schemas(registry_off)
    assert _records(registry_on) == _records(registry_off)
    assert len(registry_on.schemas) == len(registry_off.schemas) == 23


def test_request_approval_execution_smoke_is_equivalent(monkeypatch, service) -> None:
    # Arrange / Act — flag off
    _strip_feature_env(monkeypatch)
    off = _flag_off_registry(service).execute(
        "request_approval", {"action": "publish_investment_memo"}
    )
    # flag on
    _strip_feature_env(monkeypatch, keep={"DOGE_FEATURE_SLOT_PLATFORM"})
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    on = _flag_on_registry(service).execute(
        "request_approval", {"action": "publish_investment_memo"}
    )
    # Assert — same tool name, both return dict payloads
    assert off.name == on.name == "request_approval"
    assert isinstance(off.data, dict) and isinstance(on.data, dict)


def test_unknown_tool_error_is_equivalent(monkeypatch, service) -> None:
    # Arrange / Act — flag off
    _strip_feature_env(monkeypatch)
    off = _flag_off_registry(service).execute("not_a_real_tool")
    # flag on
    _strip_feature_env(monkeypatch, keep={"DOGE_FEATURE_SLOT_PLATFORM"})
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    on = _flag_on_registry(service).execute("not_a_real_tool")
    # Assert — both surface a safe unknown-tool failure
    assert off.ok is False and on.ok is False
    assert off.error == on.error


def test_tool_contribution_without_executor_fails_fast(monkeypatch, service) -> None:
    registry = SlotRegistry()
    registry.register(_BadToolSlot())
    monkeypatch.setattr(slots_module, "build_builtin_slot_registry", lambda: registry)
    _strip_feature_env(monkeypatch, keep={"DOGE_FEATURE_SLOT_PLATFORM"})
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    reset_settings()

    with pytest.raises(SlotConfigurationError, match="executor"):
        slots_module.build_slot_aware_tool_registry(lambda: _FakeGatewayContainer(service))

"""GovernanceActionsSlot unit tests."""

from __future__ import annotations

import pytest

from doge.platform.governance.actions_slot import GovernanceActionsSlot
from doge.platform.slots import SlotConfigurationError, SlotContext, SlotType

_EXPECTED_TOOLS = (
    "request_approval",
    "publish_investment_memo",
)


def test_manifest_fields_match_v1_schema() -> None:
    manifest = GovernanceActionsSlot().manifest()

    assert manifest.id == "governance.actions"
    assert manifest.type is SlotType.TOOL
    assert manifest.maturity == "experimental"
    assert manifest.feature_flags == ("slot_platform",)
    assert manifest.provides.tools == _EXPECTED_TOOLS
    assert manifest.permissions.risk_level == "medium"
    assert manifest.permissions.database == "none"
    assert manifest.health.status == "experimental"
    assert "implementation_grouping" in manifest.provides.metadata


def test_resolve_returns_two_descriptors_with_service_as_executor(stub_tool_service_factory) -> None:
    service = stub_tool_service_factory(_EXPECTED_TOOLS)
    context = SlotContext(
        settings=object(),
        feature_flags={"slot_platform": True},
        tool_application_service=service,
    )

    contribution = GovernanceActionsSlot().resolve(context)

    assert contribution.slot_id == "governance.actions"
    assert [descriptor.name for descriptor in contribution.tools] == list(_EXPECTED_TOOLS)
    assert contribution.executor is service


def test_resolve_fails_when_declared_tools_are_missing(stub_tool_service_factory) -> None:
    service = stub_tool_service_factory(_EXPECTED_TOOLS[:-1])
    context = SlotContext(
        settings=object(),
        feature_flags={"slot_platform": True},
        tool_application_service=service,
    )

    with pytest.raises(SlotConfigurationError, match="publish_investment_memo"):
        GovernanceActionsSlot().resolve(context)


def test_resolve_fails_without_tool_application_service() -> None:
    context = SlotContext(settings=object(), feature_flags={"slot_platform": True})

    with pytest.raises(SlotConfigurationError, match="tool_application_service"):
        GovernanceActionsSlot().resolve(context)

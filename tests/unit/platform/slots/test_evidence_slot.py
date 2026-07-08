"""EvidenceCoreSlot unit tests."""

from __future__ import annotations

import pytest

from doge.platform.slots import SlotConfigurationError, SlotContext, SlotType
from doge.products.research.slot import EvidenceCoreSlot

_EXPECTED_TOOLS = (
    "validate_financial_claims",
    "generate_industry_report",
    "lookup_evidence",
    "get_financial_statements",
    "get_company_announcements",
    "calculate_financial_ratios",
    "compare_consensus_estimates",
    "get_industry_classification",
)


def test_manifest_fields_match_v1_schema() -> None:
    manifest = EvidenceCoreSlot().manifest()

    assert manifest.id == "evidence.core"
    assert manifest.type is SlotType.TOOL
    assert manifest.maturity == "experimental"
    assert manifest.feature_flags == ("slot_platform",)
    assert manifest.provides.tools == _EXPECTED_TOOLS
    assert manifest.permissions.risk_level == "low"
    assert manifest.permissions.database == "read"
    assert manifest.health.status == "experimental"
    assert "implementation_grouping" in manifest.provides.metadata


def test_resolve_returns_eight_descriptors_with_service_as_executor(stub_tool_service_factory) -> None:
    service = stub_tool_service_factory(_EXPECTED_TOOLS)
    context = SlotContext(
        settings=object(),
        feature_flags={"slot_platform": True},
        tool_application_service=service,
    )

    contribution = EvidenceCoreSlot().resolve(context)

    assert contribution.slot_id == "evidence.core"
    assert [descriptor.name for descriptor in contribution.tools] == list(_EXPECTED_TOOLS)
    assert contribution.executor is service


def test_resolve_fails_when_declared_tools_are_missing(stub_tool_service_factory) -> None:
    service = stub_tool_service_factory(_EXPECTED_TOOLS[:-1])
    context = SlotContext(
        settings=object(),
        feature_flags={"slot_platform": True},
        tool_application_service=service,
    )

    with pytest.raises(SlotConfigurationError, match="get_industry_classification"):
        EvidenceCoreSlot().resolve(context)


def test_resolve_fails_without_tool_application_service() -> None:
    context = SlotContext(settings=object(), feature_flags={"slot_platform": True})

    with pytest.raises(SlotConfigurationError, match="tool_application_service"):
        EvidenceCoreSlot().resolve(context)

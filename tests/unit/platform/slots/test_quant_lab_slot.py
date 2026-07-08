"""QuantLabSlot unit tests."""

from __future__ import annotations

import pytest

from doge.platform.slots import SlotConfigurationError, SlotContext, SlotType
from doge.products.quant.slot import QuantLabSlot

_EXPECTED_TOOLS = ("run_sql_query",)


def test_manifest_fields_match_v1_schema() -> None:
    manifest = QuantLabSlot().manifest()

    assert manifest.id == "quant.lab"
    assert manifest.type is SlotType.TOOL
    assert manifest.maturity == "experimental"
    assert manifest.feature_flags == ("slot_platform",)
    assert manifest.provides.tools == _EXPECTED_TOOLS
    assert manifest.permissions.risk_level == "low"
    assert manifest.permissions.database == "read"
    assert manifest.health.status == "experimental"
    assert "python_analysis_deferred" in manifest.provides.metadata


def test_resolve_returns_one_descriptor_with_service_as_executor(stub_tool_service_factory) -> None:
    service = stub_tool_service_factory(_EXPECTED_TOOLS)
    context = SlotContext(
        settings=object(),
        feature_flags={"slot_platform": True},
        tool_application_service=service,
    )

    contribution = QuantLabSlot().resolve(context)

    assert contribution.slot_id == "quant.lab"
    assert [descriptor.name for descriptor in contribution.tools] == list(_EXPECTED_TOOLS)
    assert contribution.executor is service


def test_resolve_fails_when_declared_tools_are_missing(stub_tool_service_factory) -> None:
    service = stub_tool_service_factory(())
    context = SlotContext(
        settings=object(),
        feature_flags={"slot_platform": True},
        tool_application_service=service,
    )

    with pytest.raises(SlotConfigurationError, match="run_sql_query"):
        QuantLabSlot().resolve(context)


def test_resolve_fails_without_tool_application_service() -> None:
    context = SlotContext(settings=object(), feature_flags={"slot_platform": True})

    with pytest.raises(SlotConfigurationError, match="tool_application_service"):
        QuantLabSlot().resolve(context)

"""MarketCoreSlot unit tests."""

from __future__ import annotations

import pytest

from doge.platform.slots import SlotConfigurationError, SlotContext, SlotType
from doge.products.market.slot import MarketCoreSlot

_EXPECTED_TOOLS = (
    "query_stock",
    "stock_overview",
    "rsrs_ranking",
    "market_breadth",
    "volume_anomalies",
    "list_views",
)


def test_manifest_fields_match_v1_schema() -> None:
    # Arrange / Act
    manifest = MarketCoreSlot().manifest()
    # Assert
    assert manifest.id == "market.core"
    assert manifest.type is SlotType.TOOL
    assert manifest.maturity == "experimental"
    assert manifest.feature_flags == ("slot_platform",)
    assert manifest.provides.tools == _EXPECTED_TOOLS
    assert manifest.permissions.risk_level == "low"
    assert manifest.permissions.database == "read"
    assert manifest.health.status == "experimental"
    # list_views grouping is documented in metadata (no code moved)
    assert "list_views_grouping" in manifest.provides.metadata


def test_resolve_returns_six_descriptors_with_service_as_executor(market_service) -> None:
    # Arrange
    slot = MarketCoreSlot()
    context = SlotContext(
        settings=object(),
        feature_flags={"slot_platform": True},
        tool_application_service=market_service,
    )
    # Act
    contribution = slot.resolve(context)
    # Assert
    assert contribution.slot_id == "market.core"
    assert [d.name for d in contribution.tools] == list(_EXPECTED_TOOLS)
    assert contribution.executor is market_service


def test_resolve_fails_when_declared_tools_are_missing(stub_service) -> None:
    """Manifest/runtime tool drift is a slot configuration error."""
    slot = MarketCoreSlot()
    context = SlotContext(
        settings=object(),
        feature_flags={"slot_platform": True},
        # Has only query_stock/stock_overview/rsrs_ranking.
        tool_application_service=stub_service,
    )
    with pytest.raises(SlotConfigurationError, match="market_breadth"):
        slot.resolve(context)

"""Built-in gateway slot tests for Sprint 041."""

from __future__ import annotations

from fastapi import APIRouter

from doge.interfaces.gateway.slot import SlotDiscoveryGatewaySlot
from doge.platform.slots import SlotContext, SlotType


def test_slot_discovery_gateway_slot_manifest() -> None:
    manifest = SlotDiscoveryGatewaySlot().manifest()

    assert manifest.id == "gateway.slots"
    assert manifest.type is SlotType.GATEWAY
    assert manifest.owner == "api-gateway"
    assert manifest.feature_flags == ("slot_platform",)
    assert manifest.provides.capabilities == (
        "gateway.routes",
        "slot.discovery",
        "slot.activation",
    )
    assert manifest.provides.metadata["router_id"] == "gateway.slots"
    assert manifest.provides.metadata["prefix"] == "/v1"
    assert "/v1/slots" in manifest.provides.metadata["paths"]
    assert "/v1/slots/install" in manifest.provides.metadata["paths"]
    assert "/v1/slot-bundles/{bundle_id}/activate" in manifest.provides.metadata["paths"]
    assert "/v1/slot-bundles/active/deactivate" in manifest.provides.metadata["paths"]
    assert "/v1/ui-panels" in manifest.provides.metadata["paths"]
    assert manifest.permissions.risk_level == "low"


def test_slot_discovery_gateway_slot_contributes_router() -> None:
    context = SlotContext(settings=object(), feature_flags={"slot_platform": True})

    contribution = SlotDiscoveryGatewaySlot().resolve(context)

    assert contribution.slot_id == "gateway.slots"
    assert len(contribution.routes) == 1
    route = contribution.routes[0]
    assert route.router_id == "gateway.slots"
    assert route.prefix == "/v1"
    assert route.tags == ("v1-slots",)
    assert route.requires_auth is True
    assert isinstance(route.router_factory(context), APIRouter)

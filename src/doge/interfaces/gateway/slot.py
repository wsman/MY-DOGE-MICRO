"""Built-in gateway route slots for v1 router contributions."""

from __future__ import annotations

from doge.platform.slots import (
    SCHEMA_VERSION,
    GatewayRouteContribution,
    ISlot,
    SlotCompatibility,
    SlotContribution,
    SlotContext,
    SlotHealth,
    SlotManifest,
    SlotPermissions,
    SlotProvides,
    SlotType,
)

_SLOTS_ROUTE_MANIFEST = SlotManifest(
    schema_version=SCHEMA_VERSION,
    id="gateway.slots",
    name="Slot Gateway Routes",
    version="1.0.0",
    type=SlotType.GATEWAY,
    owner="api-gateway",
    maturity="experimental",
    description="Contributes the v1 slot discovery and bundle activation routes.",
    entrypoint="doge.interfaces.gateway.slot.SlotDiscoveryGatewaySlot",
    provides=SlotProvides(
        capabilities=("gateway.routes", "slot.discovery", "slot.activation"),
        metadata={
            "router_id": "gateway.slots",
            "prefix": "/v1",
            "paths": (
                "/v1/slots",
                "/v1/slots/install",
                "/v1/slot-bundles",
                "/v1/slot-bundles/{bundle_id}/activate",
                "/v1/slot-bundles/active/deactivate",
                "/v1/ui-panels",
                "/v1/slots/{slot_id}",
                "/v1/slots/{slot_id}/health",
            ),
        },
    ),
    permissions=SlotPermissions(network="none", risk_level="low"),
    health=SlotHealth(status="experimental"),
    feature_flags=("slot_platform",),
    compatibility=SlotCompatibility(runtime_min="1"),
)


class SlotDiscoveryGatewaySlot(ISlot):
    """Built-in gateway slot wrapping the v1 slot discovery router."""

    def manifest(self) -> SlotManifest:
        return _SLOTS_ROUTE_MANIFEST

    def resolve(self, context: SlotContext) -> SlotContribution:
        return SlotContribution(
            slot_id="gateway.slots",
            routes=(
                GatewayRouteContribution(
                    router_id="gateway.slots",
                    router_factory=_router_factory,
                    prefix="/v1",
                    tags=("v1-slots",),
                    requires_auth=True,
                ),
            ),
        )


def _router_factory(context: SlotContext):
    from doge.interfaces.gateway.routers import slots as slots_router

    return slots_router.router

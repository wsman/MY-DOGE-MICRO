"""Gateway route slot consumer parity tests (Sprint 041)."""

from __future__ import annotations

import pytest
from fastapi import APIRouter, FastAPI

from doge.bootstrap.runtime_factories import slots as slots_module
from doge.config import Settings
from doge.config.settings import FeatureConfig
from doge.interfaces.api.routes import _register_v1_routes
from doge.platform.slots import (
    GatewayRouteContribution,
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


class _GatewaySlot(ISlot):
    def __init__(self, slot_id: str, *, router_id: str, router: APIRouter | None) -> None:
        self._slot_id = slot_id
        self._router_id = router_id
        self._router = router

    def manifest(self) -> SlotManifest:
        return SlotManifest(
            schema_version=1,
            id=self._slot_id,
            name="Test Gateway Slot",
            version="1.0.0",
            type=SlotType.GATEWAY,
            owner="slot-tests",
            maturity="experimental",
            description="Test gateway route slot.",
            entrypoint="tests.contract.test_gateway_slot_parity.GatewaySlot",
            provides=SlotProvides(capabilities=("gateway.routes",)),
            health=SlotHealth(status="experimental"),
            feature_flags=("slot_platform",),
        )

    def resolve(self, context: SlotContext) -> SlotContribution:
        return SlotContribution(
            slot_id=self._slot_id,
            routes=(
                GatewayRouteContribution(
                    router_id=self._router_id,
                    router_factory=lambda _context: self._router,
                    prefix="/v1",
                    tags=("test",),
                ),
            ),
        )


def test_gateway_slot_off_preserves_v1_route_set() -> None:
    flag_off = FastAPI()
    flag_on = FastAPI()

    _register_v1_routes(flag_off, _settings(slot_platform=False))
    _register_v1_routes(flag_on, _settings(slot_platform=True))

    assert _route_rows(flag_on) == _route_rows(flag_off)
    assert ("GET", "/v1/slots", "list_slots") in _route_rows(flag_on)
    assert ("GET", "/v1/ui-panels", "list_ui_panels") in _route_rows(flag_on)
    assert ("GET", "/v1/slots/{slot_id}", "get_slot") in _route_rows(flag_on)
    assert (
        "GET",
        "/v1/slots/{slot_id}/health",
        "get_slot_health",
    ) in _route_rows(flag_on)


def test_build_slot_aware_gateway_routes_mounts_builtin_slots_router() -> None:
    app = FastAPI()

    mounted = slots_module.build_slot_aware_gateway_routes(
        app,
        settings=_settings(slot_platform=True),
    )

    assert mounted == ("gateway.slots",)
    assert ("GET", "/v1/slots", "list_slots") in _route_rows(app)
    assert ("GET", "/v1/ui-panels", "list_ui_panels") in _route_rows(app)


def test_gateway_route_duplicate_router_ids_fail_fast(monkeypatch) -> None:
    registry = SlotRegistry()
    registry.register(_GatewaySlot("gateway.one", router_id="gateway.duplicate", router=APIRouter()))
    registry.register(_GatewaySlot("gateway.two", router_id="gateway.duplicate", router=APIRouter()))
    monkeypatch.setattr(slots_module, "build_builtin_slot_registry", lambda: registry)

    with pytest.raises(SlotConfigurationError, match="duplicate gateway route"):
        slots_module.build_slot_aware_gateway_routes(
            FastAPI(),
            settings=_settings(slot_platform=True),
        )


def test_gateway_route_factory_returning_none_fails_fast(monkeypatch) -> None:
    registry = SlotRegistry()
    registry.register(_GatewaySlot("gateway.none", router_id="gateway.none", router=None))
    monkeypatch.setattr(slots_module, "build_builtin_slot_registry", lambda: registry)

    with pytest.raises(SlotConfigurationError, match="returned no router"):
        slots_module.build_slot_aware_gateway_routes(
            FastAPI(),
            settings=_settings(slot_platform=True),
        )


def _settings(*, slot_platform: bool) -> Settings:
    return Settings(features=FeatureConfig(slot_platform=slot_platform))


def _route_rows(app: FastAPI) -> set[tuple[str, str, str]]:
    rows: set[tuple[str, str, str]] = set()
    for route in app.routes:
        methods = sorted(
            method
            for method in getattr(route, "methods", set())
            if method not in {"HEAD", "OPTIONS"}
        )
        for method in methods:
            rows.add((method, getattr(route, "path", ""), getattr(route, "name", "")))
    return rows

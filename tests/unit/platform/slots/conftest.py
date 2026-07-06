"""Shared fixtures and stubs for slot-platform unit tests."""

from __future__ import annotations

from typing import Any, Iterable

import pytest

from doge.core.domain.tool_descriptor import ToolDescriptor
from doge.core.domain.tool_policy import ToolCategory
from doge.platform.slots import (
    ISlot,
    SlotContribution,
    SlotContext,
    SlotManifest,
    load_slot_manifest,
)


def _descriptor(name: str) -> ToolDescriptor:
    return ToolDescriptor(
        name=name,
        description=f"stub tool {name}",
        category=ToolCategory.READ_ONLY,
    )


class StubToolService:
    """Minimal ``ToolServiceProtocol`` returning canned descriptors.

    Also exposes each tool name as an attribute so the
    ``ToolRegistry.include_descriptors`` ``getattr`` seam would resolve.
    """

    def __init__(self, names: Iterable[str]) -> None:
        self._descriptors = tuple(_descriptor(n) for n in names)
        for d in self._descriptors:
            setattr(self, d.name, lambda *args, **kwargs: {"ok": True})

    def tool_descriptors(self) -> tuple[ToolDescriptor, ...]:
        return self._descriptors


class StubSlot(ISlot):
    """Minimal ``ISlot`` resolving a subset of a stub service's descriptors."""

    def __init__(self, manifest: SlotManifest, service: StubToolService) -> None:
        self._manifest = manifest
        self._service = service

    def manifest(self) -> SlotManifest:
        return self._manifest

    def resolve(self, context: SlotContext) -> SlotContribution:
        wanted = set(self._manifest.provides.tools)
        tools = tuple(d for d in self._service.tool_descriptors() if d.name in wanted)
        return SlotContribution(
            slot_id=self._manifest.id, tools=tools, executor=self._service
        )


def _base_manifest_dict(slot_id: str = "market.core") -> dict[str, Any]:
    return {
        "schema_version": 1,
        "id": slot_id,
        "name": "Market Core",
        "version": "1.0.0",
        "type": "tool",
        "owner": "market-intelligence",
        "maturity": "experimental",
        "description": "Ticker lookup, market breadth, RSRS ranking, volume anomalies.",
        "entrypoint": "doge.products.market.slot.MarketCoreSlot",
        "provides": {"tools": ["query_stock", "stock_overview"]},
        "permissions": {"database": "read", "risk_level": "low"},
        "health": {"status": "experimental"},
        "feature_flags": ["slot_platform"],
        "compatibility": {"runtime_min": "1"},
    }


@pytest.fixture
def valid_manifest_dict() -> dict[str, Any]:
    return _base_manifest_dict()


@pytest.fixture
def stub_service() -> StubToolService:
    return StubToolService(["query_stock", "stock_overview", "rsrs_ranking"])


@pytest.fixture
def market_service() -> StubToolService:
    """Stub service exposing all six market.core tool names."""
    return StubToolService(
        [
            "query_stock",
            "stock_overview",
            "rsrs_ranking",
            "market_breadth",
            "volume_anomalies",
            "list_views",
        ]
    )


@pytest.fixture
def stub_slot(valid_manifest_dict: dict[str, Any], stub_service: StubToolService) -> StubSlot:
    return StubSlot(load_slot_manifest(valid_manifest_dict), stub_service)


@pytest.fixture
def second_stub_slot(stub_service: StubToolService) -> StubSlot:
    return StubSlot(load_slot_manifest(_base_manifest_dict("other.slot")), stub_service)


@pytest.fixture
def slot_context_factory(stub_service: StubToolService):
    def _make(feature_flags: dict[str, bool] | None = None) -> SlotContext:
        return SlotContext(
            settings=object(),
            feature_flags=feature_flags if feature_flags is not None else {"slot_platform": True},
            tool_application_service=stub_service,
        )

    return _make

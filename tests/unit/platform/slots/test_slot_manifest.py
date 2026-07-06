"""SlotManifest v1 schema validation contract tests.

Each validation rule has a dedicated failure case; the strict loader also
rejects unknown top-level keys and accepts JSON-file inputs.
"""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError

import pytest

from doge.platform.slots import (
    SCHEMA_VERSION,
    SlotManifestValidationError,
    SlotType,
    load_slot_manifest,
)


def _dict(**overrides) -> dict:
    base = {
        "schema_version": 1,
        "id": "market.core",
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
    base.update(overrides)
    return base


def test_valid_manifest_loads_with_expected_fields() -> None:
    # Arrange / Act
    manifest = load_slot_manifest(_dict())
    # Assert
    assert manifest.schema_version == SCHEMA_VERSION
    assert manifest.id == "market.core"
    assert manifest.type is SlotType.TOOL
    assert manifest.maturity == "experimental"
    assert manifest.provides.tools == ("query_stock", "stock_overview")
    assert manifest.feature_flags == ("slot_platform",)
    assert manifest.permissions.database == "read"
    assert manifest.permissions.risk_level == "low"
    assert manifest.health.status == "experimental"


@pytest.mark.parametrize(
    "bad_id",
    ["Market.Core", "-market.core", "market..core", "9market", "market.core!", "x" * 65],
)
def test_invalid_id_rejected(bad_id: str) -> None:
    # Arrange / Act / Assert
    with pytest.raises(SlotManifestValidationError):
        load_slot_manifest(_dict(id=bad_id))


def test_unknown_type_rejected() -> None:
    with pytest.raises(SlotManifestValidationError):
        load_slot_manifest(_dict(type="not-a-type"))


def test_unknown_top_level_key_rejected() -> None:
    payload = _dict()
    payload["surprise_field"] = 1
    with pytest.raises(SlotManifestValidationError):
        load_slot_manifest(payload)


def test_provides_must_declare_a_tool_or_capability() -> None:
    with pytest.raises(SlotManifestValidationError):
        load_slot_manifest(_dict(provides={"tools": [], "capabilities": []}))


def test_wrong_schema_version_rejected() -> None:
    with pytest.raises(SlotManifestValidationError):
        load_slot_manifest(_dict(schema_version=2))


def test_bad_risk_level_rejected() -> None:
    with pytest.raises(SlotManifestValidationError):
        load_slot_manifest(_dict(permissions={"risk_level": "extreme"}))


def test_bad_maturity_rejected() -> None:
    with pytest.raises(SlotManifestValidationError):
        load_slot_manifest(_dict(maturity="GA"))


def test_missing_required_field_rejected() -> None:
    payload = _dict()
    del payload["entrypoint"]
    with pytest.raises(SlotManifestValidationError):
        load_slot_manifest(payload)


def test_manifest_is_frozen() -> None:
    manifest = load_slot_manifest(_dict())
    with pytest.raises(FrozenInstanceError):
        manifest.id = "other"  # type: ignore[misc]


def test_json_path_loader_round_trips(tmp_path) -> None:
    # Arrange
    path = tmp_path / "market.core.json"
    path.write_text(json.dumps(_dict()), encoding="utf-8")
    # Act
    manifest = load_slot_manifest(path)
    # Assert
    assert manifest.id == "market.core"
    assert manifest.type is SlotType.TOOL


def test_non_json_path_rejected(tmp_path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(SlotManifestValidationError):
        load_slot_manifest(path)

from __future__ import annotations

import json

import pytest

from doge.platform.slots import SlotConfigurationError, SlotLoader, SlotType


def test_slot_loader_loads_manifest_json_file(tmp_path) -> None:
    path = tmp_path / "local.slot.json"
    path.write_text(json.dumps(_manifest("local.preview")), encoding="utf-8")

    [slot] = SlotLoader().load([path])

    assert slot.manifest().id == "local.preview"
    assert slot.manifest().type is SlotType.WORKFLOW
    assert slot.resolve(_context()).slot_id == "local.preview"


def test_slot_loader_discovers_direct_and_nested_json_manifests(tmp_path) -> None:
    direct = tmp_path / "direct.json"
    nested_dir = tmp_path / "nested"
    nested_dir.mkdir()
    nested = nested_dir / "slot.json"
    direct.write_text(json.dumps(_manifest("local.direct")), encoding="utf-8")
    nested.write_text(json.dumps(_manifest("local.nested")), encoding="utf-8")

    slots = SlotLoader().load([tmp_path])

    assert [slot.manifest().id for slot in slots] == ["local.direct", "local.nested"]


def test_slot_loader_rejects_missing_source(tmp_path) -> None:
    with pytest.raises(SlotConfigurationError, match="does not exist"):
        SlotLoader().load([tmp_path / "missing"])


def test_slot_loader_annotates_invalid_manifest_path(tmp_path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{}", encoding="utf-8")

    with pytest.raises(SlotConfigurationError, match="failed to load slot manifest"):
        SlotLoader().load([path])


def _manifest(slot_id: str) -> dict:
    return {
        "schema_version": 1,
        "id": slot_id,
        "name": "Local Preview",
        "version": "0.1.0",
        "type": "workflow",
        "owner": "doge.local",
        "maturity": "experimental",
        "description": "Local manifest-only slot for loader tests.",
        "entrypoint": "doge.local.preview",
        "provides": {"capabilities": ["local_preview"]},
        "feature_flags": ["slot_platform"],
    }


def _context():
    from doge.platform.slots import SlotContext

    return SlotContext(settings=object(), feature_flags={"slot_platform": True})

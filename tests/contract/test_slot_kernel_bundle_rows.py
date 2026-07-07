from __future__ import annotations

import json

from doge.bootstrap.runtime_factories.slots import (
    activate_slot_bundle,
    build_builtin_slot_kernel,
    build_slot_status_rows,
    build_slot_bundle_rows,
    clear_slot_bundle_activation,
    install_slot,
)
from doge.config import Settings, get_settings, reset_settings
from doge.config.settings import FeatureConfig, SlotConfig
from doge.platform.slots import SlotPolicy, SlotStatusRecord, load_slot_manifest


def test_builtin_slot_kernel_exposes_builtin_bundles() -> None:
    kernel = build_builtin_slot_kernel()

    assert [bundle.id for bundle in kernel.bundles()] == [
        "bundle.local_analyst",
        "bundle.daemon_operator",
        "bundle.research_workspace",
        "bundle.enterprise_safe",
    ]


def test_slot_bundle_rows_reflect_feature_flags() -> None:
    rows = build_slot_bundle_rows(
        Settings(features=FeatureConfig(slot_platform=True, workflow_templates=False))
    )

    local = next(row for row in rows if row["id"] == "bundle.local_analyst")

    assert local["status"] == "partial"
    assert "market.core" in local["enabled_slot_ids"]
    assert "workflow.templates" in local["disabled_slot_ids"]
    assert local["counts"]["missing"] == 0


def test_slot_bundle_rows_are_disabled_when_slot_platform_is_off() -> None:
    rows = build_slot_bundle_rows(Settings(features=FeatureConfig(slot_platform=False)))

    assert {row["status"] for row in rows} == {"disabled"}


def test_builtin_slot_kernel_can_accept_policy() -> None:
    kernel = build_builtin_slot_kernel(
        policy=SlotPolicy(enabled_slots=("market.core",)),
    )

    rows = build_slot_bundle_rows(Settings(features=FeatureConfig(slot_platform=True)))
    status_records = {
        record.id: record.status
        for record in kernel.status(
            kernel_context(Settings(features=FeatureConfig(slot_platform=True)))
        )
    }

    assert rows
    assert status_records["market.core"] == "resolved"
    assert status_records["model.kimi_agent_sdk"] == "disabled"


def test_slot_loader_adds_manifest_only_slots_when_enabled(tmp_path, monkeypatch) -> None:
    clear_slot_bundle_activation()
    (tmp_path / "slot.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "id": "local.preview",
                "name": "Local Preview",
                "version": "0.1.0",
                "type": "workflow",
                "owner": "doge.local",
                "maturity": "experimental",
                "description": "Local manifest-only slot for loader parity.",
                "entrypoint": "doge.local.preview",
                "provides": {"capabilities": ["local_preview"]},
                "feature_flags": ["slot_platform"],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    monkeypatch.setenv("DOGE_FEATURE_SLOT_LOADER", "1")
    monkeypatch.setenv("DOGE_SLOT_MANIFEST_DIRS", str(tmp_path))
    reset_settings()

    try:
        rows = build_slot_status_rows(get_settings())
    finally:
        monkeypatch.delenv("DOGE_FEATURE_SLOT_PLATFORM", raising=False)
        monkeypatch.delenv("DOGE_FEATURE_SLOT_LOADER", raising=False)
        monkeypatch.delenv("DOGE_SLOT_MANIFEST_DIRS", raising=False)
        reset_settings()

    local = next(row for row in rows if row["id"] == "local.preview")
    assert local["status"] == "resolved"
    assert local["type"] == "workflow"


def test_slot_loader_uses_explicit_settings_without_global_env(tmp_path) -> None:
    (tmp_path / "slot.json").write_text(
        json.dumps(_manifest("local.explicit")),
        encoding="utf-8",
    )

    rows = build_slot_status_rows(
        Settings(
            features=FeatureConfig(slot_platform=True, slot_loader=True),
            slots=SlotConfig(manifest_dirs=(tmp_path,)),
        )
    )

    local = next(row for row in rows if row["id"] == "local.explicit")
    assert local["status"] == "resolved"


def test_slot_bundle_activation_marks_active_bundle_and_filters_policy(monkeypatch) -> None:
    clear_slot_bundle_activation()
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    monkeypatch.setenv("DOGE_FEATURE_SLOT_LOADER", "1")
    reset_settings()

    try:
        payload = activate_slot_bundle("bundle.daemon_operator", settings=get_settings())
        rows = build_slot_bundle_rows(get_settings())
        kernel = build_builtin_slot_kernel()
        status_records = {
            record.id: record.status
            for record in kernel.status(kernel_context(get_settings()))
        }
    finally:
        clear_slot_bundle_activation()
        monkeypatch.delenv("DOGE_FEATURE_SLOT_PLATFORM", raising=False)
        monkeypatch.delenv("DOGE_FEATURE_SLOT_LOADER", raising=False)
        reset_settings()

    assert payload["status"] == "activated"
    assert payload["bundle"]["active"] is True
    assert next(row for row in rows if row["id"] == "bundle.daemon_operator")["active"] is True
    assert status_records["gateway.slots"] == "resolved"
    assert status_records["market.core"] == "disabled"


def test_slot_install_dir_is_loaded_as_manifest_only_source(tmp_path, monkeypatch) -> None:
    source = tmp_path / "source" / "slot.json"
    source.parent.mkdir()
    source.write_text(json.dumps(_manifest("local.installed")), encoding="utf-8")
    install_dir = tmp_path / "installed"
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    monkeypatch.setenv("DOGE_FEATURE_SLOT_LOADER", "1")
    monkeypatch.setenv("DOGE_FEATURE_SLOT_INSTALL", "1")
    monkeypatch.setenv("DOGE_SLOT_INSTALL_DIR", str(install_dir))
    reset_settings()

    try:
        payload = install_slot(str(source.parent), settings=get_settings())
        rows = build_slot_status_rows(get_settings())
    finally:
        monkeypatch.delenv("DOGE_FEATURE_SLOT_PLATFORM", raising=False)
        monkeypatch.delenv("DOGE_FEATURE_SLOT_LOADER", raising=False)
        monkeypatch.delenv("DOGE_FEATURE_SLOT_INSTALL", raising=False)
        monkeypatch.delenv("DOGE_SLOT_INSTALL_DIR", raising=False)
        reset_settings()

    assert payload["status"] == "installed"
    local = next(row for row in rows if row["id"] == "local.installed")
    assert local["status"] == "resolved"
    assert local["entrypoint"] == "doge.local.preview"


def test_slot_status_rows_use_kernel_active_health(monkeypatch) -> None:
    from doge.bootstrap.runtime_factories import slots as slot_factories

    manifest = load_slot_manifest(
        {
            "schema_version": 1,
            "id": "health.dynamic",
            "name": "Dynamic Health",
            "version": "0.1.0",
            "type": "workflow",
            "owner": "doge.local",
            "maturity": "experimental",
            "description": "Dynamic health row test.",
            "entrypoint": "doge.local.dynamic",
            "provides": {"capabilities": ["dynamic_health"]},
            "health": {"status": "healthy"},
            "feature_flags": ["slot_platform"],
        }
    )

    class _Slot:
        def manifest(self):
            return manifest

    class _Registry:
        def all(self):
            return (_Slot(),)

    class _Kernel:
        registry = _Registry()

        def status(self, context):
            return (
                SlotStatusRecord(
                    id="health.dynamic",
                    name="Dynamic Health",
                    type="workflow",
                    status="disabled",
                    tools_count=0,
                    health="disabled",
                    feature_flags=("slot_platform",),
                ),
            )

    monkeypatch.setattr(slot_factories, "build_builtin_slot_kernel", lambda **kwargs: _Kernel())

    [row] = slot_factories.build_slot_status_rows(
        Settings(features=FeatureConfig(slot_platform=True))
    )

    assert row["status"] == "disabled"
    assert row["health"]["status"] == "disabled"


def kernel_context(settings: Settings):
    from doge.bootstrap.runtime_factories.slots import _feature_flags
    from doge.platform.slots import SlotContext

    return SlotContext(settings=settings, feature_flags=_feature_flags(settings))


def _manifest(slot_id: str) -> dict:
    return {
        "schema_version": 1,
        "id": slot_id,
        "name": "Local Installed",
        "version": "0.1.0",
        "type": "workflow",
        "owner": "doge.local",
        "maturity": "experimental",
        "description": "Local installed manifest-only slot.",
        "entrypoint": "doge.local.preview",
        "provides": {"capabilities": ["local_preview"]},
        "feature_flags": ["slot_platform"],
    }

from __future__ import annotations

import base64
import json
import sys
import uuid
from dataclasses import fields
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from doge.bootstrap.runtime_factories.slots import (
    build_builtin_slot_kernel,
    build_slot_status_rows,
)
from doge.config.settings import AuthConfig, DBConfig, FeatureConfig, Settings, SlotConfig
from doge.infrastructure.database.slot_signing_repository import SQLiteSlotSigningRepository
from doge.platform.slots import SlotConfigurationError, SlotContext, SlotType, sign_slot_manifest


def test_provider_execution_default_off_keeps_installed_slot_manifest_only(
    tmp_path, monkeypatch
) -> None:
    installed = _installed_provider(tmp_path, monkeypatch)
    settings = _settings(tmp_path, installed, provider_execution=False)

    rows = build_slot_status_rows(settings)

    row = _row(rows, installed.slot_id)
    assert row["execution_eligible"] is False
    assert "manifest-only slot" in row["execution_blockers"]
    assert "slot_provider_execution disabled" in row["execution_blockers"]
    assert not installed.import_marker.exists()


def test_provider_execution_status_reports_eligible_without_importing_provider(
    tmp_path, monkeypatch
) -> None:
    installed = _installed_provider(tmp_path, monkeypatch)
    settings = _settings(tmp_path, installed, provider_execution=True)

    rows = build_slot_status_rows(settings)

    row = _row(rows, installed.slot_id)
    assert row["execution_eligible"] is True
    assert row["execution"]["signature"]["status"] == "verified"
    assert row["execution"]["signature"]["revocation_checked"] is True
    assert not installed.import_marker.exists()


def test_provider_execution_imports_and_resolves_only_after_all_gates_pass(
    tmp_path, monkeypatch
) -> None:
    installed = _installed_provider(tmp_path, monkeypatch)
    settings = _settings(tmp_path, installed, provider_execution=True)
    kernel = build_builtin_slot_kernel(settings=settings)
    context = SlotContext(settings=settings, feature_flags=_feature_flags(settings))

    contributions = kernel.resolve_contributions(context, slot_type=SlotType.WORKFLOW)

    contribution = next(item for item in contributions if item.slot_id == installed.slot_id)
    assert contribution.workflows[0].slug == "third-party-workflow"
    assert installed.import_marker.read_text(encoding="utf-8") == "imported"


def test_provider_execution_requires_verified_signature(tmp_path, monkeypatch) -> None:
    installed = _installed_provider(tmp_path, monkeypatch, signed=False)
    settings = _settings(tmp_path, installed, provider_execution=True)

    row = _row(build_slot_status_rows(settings), installed.slot_id)

    assert row["execution_eligible"] is False
    assert "signature missing" in row["execution_blockers"]
    assert not installed.import_marker.exists()


def test_provider_execution_requires_non_revoked_signing_key(
    tmp_path, monkeypatch
) -> None:
    installed = _installed_provider(tmp_path, monkeypatch)
    settings = _settings(tmp_path, installed, provider_execution=True)
    SQLiteSlotSigningRepository(settings.db.agent_db).revoke(
        "ops-key",
        reason="compromised",
        actor_hash="test",
    )

    row = _row(build_slot_status_rows(settings), installed.slot_id)

    assert row["execution_eligible"] is False
    assert "signature revoked: key_id is revoked" in row["execution_blockers"]
    assert not installed.import_marker.exists()


def test_provider_execution_requires_enterprise_allowlist(tmp_path, monkeypatch) -> None:
    installed = _installed_provider(tmp_path, monkeypatch)
    settings = _settings(
        tmp_path,
        installed,
        provider_execution=True,
        enterprise=True,
        allowlist=(),
    )

    row = _row(build_slot_status_rows(settings), installed.slot_id)

    assert row["execution_eligible"] is False
    assert "slot is not enterprise allowlisted" in row["execution_blockers"]
    assert not installed.import_marker.exists()


def test_provider_execution_requires_runtime_interception(tmp_path, monkeypatch) -> None:
    installed = _installed_provider(tmp_path, monkeypatch)
    settings = _settings(
        tmp_path,
        installed,
        provider_execution=True,
        runtime_interception=False,
    )

    row = _row(build_slot_status_rows(settings), installed.slot_id)

    assert row["execution_eligible"] is False
    assert "slot_runtime_interception disabled" in row["execution_blockers"]
    assert not installed.import_marker.exists()


def test_provider_execution_rejects_restricted_contribution_facets(
    tmp_path, monkeypatch
) -> None:
    installed = _installed_provider(tmp_path, monkeypatch, restricted_facet=True)
    settings = _settings(tmp_path, installed, provider_execution=True)
    kernel = build_builtin_slot_kernel(settings=settings)
    context = SlotContext(settings=settings, feature_flags=_feature_flags(settings))

    with pytest.raises(SlotConfigurationError, match="restricted facet routes"):
        kernel.resolve_contributions(context, slot_type=SlotType.WORKFLOW)

    assert installed.import_marker.exists()


def test_manifest_dir_slots_remain_non_installed_manifest_only(
    tmp_path, monkeypatch
) -> None:
    installed = _installed_provider(tmp_path, monkeypatch)
    manifest_dir = tmp_path / "manifest-dir"
    manifest_dir.mkdir()
    manifest = _manifest(installed.slot_id, installed.entrypoint)
    (manifest_dir / "direct.json").write_text(json.dumps(manifest), encoding="utf-8")
    settings = _settings(
        tmp_path,
        installed,
        provider_execution=True,
        install_dir=tmp_path / "empty-install-dir",
        manifest_dirs=(manifest_dir,),
    )

    row = _row(build_slot_status_rows(settings), installed.slot_id)

    assert row["execution_eligible"] is False
    assert "not installed slot" in row["execution_blockers"]
    assert not installed.import_marker.exists()


class _InstalledFixture:
    def __init__(
        self,
        *,
        slot_id: str,
        entrypoint: str,
        install_dir: Path,
        public_key: str,
        import_marker: Path,
    ) -> None:
        self.slot_id = slot_id
        self.entrypoint = entrypoint
        self.install_dir = install_dir
        self.public_key = public_key
        self.import_marker = import_marker


def _installed_provider(
    tmp_path,
    monkeypatch,
    *,
    signed: bool = True,
    restricted_facet: bool = False,
) -> _InstalledFixture:
    module_name = f"p5_provider_{uuid.uuid4().hex}"
    slot_id = f"vendor.p{uuid.uuid4().hex}"
    import_marker = tmp_path / f"{module_name}.imported"
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setenv("P5_PROVIDER_IMPORT_MARKER", str(import_marker))
    Path(tmp_path / f"{module_name}.py").write_text(
        _provider_module(slot_id, restricted_facet=restricted_facet),
        encoding="utf-8",
    )
    sys.modules.pop(module_name, None)

    install_dir = tmp_path / "installed"
    slot_dir = install_dir / slot_id.replace(".", "_")
    slot_dir.mkdir(parents=True)
    entrypoint = f"{module_name}.ProviderSlot"
    manifest_path = slot_dir / "slot.json"
    manifest_path.write_text(
        json.dumps(_manifest(slot_id, entrypoint), sort_keys=True),
        encoding="utf-8",
    )
    private_key_path, public_key = _write_private_key(slot_dir)
    if signed:
        sign_slot_manifest(
            manifest_path,
            private_key_path=private_key_path,
            key_id="ops-key",
        )
    return _InstalledFixture(
        slot_id=slot_id,
        entrypoint=entrypoint,
        install_dir=install_dir,
        public_key=public_key,
        import_marker=import_marker,
    )


def _settings(
    tmp_path,
    installed: _InstalledFixture,
    *,
    provider_execution: bool,
    runtime_interception: bool = True,
    enterprise: bool = False,
    allowlist: tuple[str, ...] | None = None,
    install_dir: Path | None = None,
    manifest_dirs: tuple[Path, ...] = (),
) -> Settings:
    return Settings(
        db=DBConfig(dir=tmp_path / "db"),
        auth=AuthConfig(mode="enterprise" if enterprise else "local_demo"),
        features=FeatureConfig(
            slot_platform=True,
            slot_loader=True,
            slot_install=True,
            slot_runtime_interception=runtime_interception,
            slot_provider_execution=provider_execution,
        ),
        slots=SlotConfig(
            manifest_dirs=manifest_dirs,
            install_dir=install_dir or installed.install_dir,
            enterprise_allowlist=allowlist
            if allowlist is not None
            else ((installed.slot_id,) if enterprise else ()),
            trusted_publisher_keys={"ops-key": installed.public_key},
            allow_unsigned_local=False,
        ),
    )


def _feature_flags(settings: Settings) -> dict[str, bool]:
    return {
        field.name: getattr(settings.features, field.name)
        for field in fields(settings.features)
        if isinstance(getattr(settings.features, field.name), bool)
    }


def _row(rows, slot_id: str) -> dict:
    return next(row for row in rows if row["id"] == slot_id)


def _manifest(slot_id: str, entrypoint: str) -> dict:
    return {
        "schema_version": 1,
        "id": slot_id,
        "name": "Third-party Workflow",
        "version": "0.1.0",
        "type": "workflow",
        "owner": "vendor",
        "maturity": "experimental",
        "description": "Trusted local provider execution fixture.",
        "entrypoint": entrypoint,
        "provides": {"capabilities": ["third_party_workflow"]},
        "permissions": {"risk_level": "low"},
        "feature_flags": ["slot_platform"],
    }


def _provider_module(slot_id: str, *, restricted_facet: bool) -> str:
    restricted = (
        "routes=(GatewayRouteContribution("
        "router_id='bad-route', router_factory=lambda context: None, prefix='/bad'),)"
        if restricted_facet
        else ""
    )
    return f"""
import os
from pathlib import Path

from doge.platform.slots import (
    GatewayRouteContribution,
    ISlot,
    SlotContribution,
    SlotHealth,
    SlotManifest,
    SlotProvides,
    SlotType,
    WorkflowTemplateContribution,
)

marker = os.environ.get("P5_PROVIDER_IMPORT_MARKER")
if marker:
    Path(marker).write_text("imported", encoding="utf-8")


class ProviderSlot(ISlot):
    def manifest(self):
        return SlotManifest(
            schema_version=1,
            id={slot_id!r},
            name="Third-party Workflow",
            version="0.1.0",
            type=SlotType.WORKFLOW,
            owner="vendor",
            maturity="experimental",
            description="Trusted local provider execution fixture.",
            entrypoint=__name__ + ".ProviderSlot",
            provides=SlotProvides(capabilities=("third_party_workflow",)),
            health=SlotHealth(status="experimental"),
            feature_flags=("slot_platform",),
        )

    def resolve(self, context):
        return SlotContribution(
            slot_id={slot_id!r},
            workflows=(
                WorkflowTemplateContribution(
                    slug="third-party-workflow",
                    template_factory=lambda context: {{"slug": "third-party-workflow"}},
                ),
            ),
            {restricted}
        )
"""


def _write_private_key(directory: Path) -> tuple[Path, str]:
    private_key = Ed25519PrivateKey.generate()
    private_key_path = directory / "ops-key.pem"
    private_key_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return private_key_path, base64.b64encode(public_key).decode("ascii")

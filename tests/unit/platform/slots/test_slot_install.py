from __future__ import annotations

import hashlib
import json

import pytest

from doge.platform.slots import (
    SlotConfigurationError,
    SlotInstallPolicy,
    SlotInstaller,
    verify_slot_signature,
)


def test_local_unsigned_install_copies_manifest_and_warns(tmp_path) -> None:
    source = tmp_path / "source" / "slot.json"
    source.parent.mkdir()
    source.write_text(json.dumps(_manifest("local.preview")), encoding="utf-8")
    install_dir = tmp_path / "installed"

    result = SlotInstaller().install(source.parent, install_dir=install_dir)
    second = SlotInstaller().install(source.parent, install_dir=install_dir)

    assert result.slot_id == "local.preview"
    assert result.status == "installed"
    assert result.installed_path == install_dir / "local_preview" / "slot.json"
    assert result.installed_path.exists()
    assert result.signature.status == "missing"
    assert result.warnings == ("unsigned local slot manifest",)
    assert second.status == "already_installed"


def test_install_rejects_high_risk_and_shell_by_default(tmp_path) -> None:
    high_risk = tmp_path / "high" / "slot.json"
    high_risk.parent.mkdir()
    high_risk.write_text(
        json.dumps(_manifest("local.high", permissions={"risk_level": "high"})),
        encoding="utf-8",
    )
    shell = tmp_path / "shell" / "slot.json"
    shell.parent.mkdir()
    shell.write_text(
        json.dumps(_manifest("local.shell", permissions={"shell": "allow"})),
        encoding="utf-8",
    )

    with pytest.raises(SlotConfigurationError, match="high risk"):
        SlotInstaller().install(high_risk.parent, install_dir=tmp_path / "installed")
    with pytest.raises(SlotConfigurationError, match="shell permission"):
        SlotInstaller().install(shell.parent, install_dir=tmp_path / "installed")


def test_enterprise_install_requires_allowlist_and_trusted_signature(tmp_path) -> None:
    source_dir = tmp_path / "signed"
    source_dir.mkdir()
    manifest_path = source_dir / "slot.json"
    manifest_path.write_text(json.dumps(_manifest("local.signed")), encoding="utf-8")
    _write_signature(manifest_path, "local.signed", signer="ops")

    with pytest.raises(SlotConfigurationError, match="not enterprise allowlisted"):
        SlotInstaller().install(
            source_dir,
            install_dir=tmp_path / "installed",
            policy=SlotInstallPolicy(auth_mode="enterprise", trusted_signers=("ops",)),
        )

    result = SlotInstaller().install(
        source_dir,
        install_dir=tmp_path / "installed",
        policy=SlotInstallPolicy(
            auth_mode="enterprise",
            enterprise_allowlist=("local.signed",),
            trusted_signers=("ops",),
        ),
    )

    assert result.status == "installed"
    assert result.signature.status == "verified"
    assert (tmp_path / "installed" / "local_signed" / "slot.signature.json").exists()


def test_invalid_signature_hash_is_rejected(tmp_path) -> None:
    source_dir = tmp_path / "signed"
    source_dir.mkdir()
    manifest_path = source_dir / "slot.json"
    manifest_path.write_text(json.dumps(_manifest("local.bad")), encoding="utf-8")
    (source_dir / "slot.signature.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "slot_id": "local.bad",
                "manifest_sha256": "bad",
                "signer": "ops",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(SlotConfigurationError, match="invalid signature"):
        SlotInstaller().install(manifest_path, install_dir=tmp_path / "installed")


def test_untrusted_signature_reports_untrusted_status(tmp_path) -> None:
    manifest_path = tmp_path / "slot.json"
    manifest_path.write_text(json.dumps(_manifest("local.untrusted")), encoding="utf-8")
    _write_signature(manifest_path, "local.untrusted", signer="someone")

    signature = verify_slot_signature(
        manifest_path,
        slot_id="local.untrusted",
        trusted_signers=("ops",),
    )

    assert signature.status == "untrusted"
    assert signature.signer == "someone"


def _manifest(slot_id: str, *, permissions: dict | None = None) -> dict:
    return {
        "schema_version": 1,
        "id": slot_id,
        "name": "Local Preview",
        "version": "0.1.0",
        "type": "workflow",
        "owner": "doge.local",
        "maturity": "experimental",
        "description": "Local third-party manifest-only slot preview.",
        "entrypoint": "doge.local.preview",
        "provides": {"capabilities": ["local_preview"]},
        "permissions": permissions or {},
        "feature_flags": ["slot_platform"],
    }


def _write_signature(manifest_path, slot_id: str, *, signer: str) -> None:
    digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    (manifest_path.parent / "slot.signature.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "slot_id": slot_id,
                "manifest_sha256": digest,
                "signer": signer,
            }
        ),
        encoding="utf-8",
    )

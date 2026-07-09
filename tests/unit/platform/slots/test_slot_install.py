from __future__ import annotations

import base64
import hashlib
import json

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import doge.platform.slots.install as slot_install_module
from doge.platform.slots import (
    SlotConfigurationError,
    SlotInstallPolicy,
    SlotInstaller,
    package_tree_digest,
    sign_slot_manifest,
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


def test_install_cleans_staged_directory_when_copy_fails(tmp_path, monkeypatch) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    manifest_path = source_dir / "slot.json"
    manifest_path.write_text(json.dumps(_manifest("local.rollback")), encoding="utf-8")
    _write_legacy_signature(manifest_path, "local.rollback", signer="ops")
    install_dir = tmp_path / "installed"
    original_copyfile = slot_install_module.shutil.copyfile

    def fail_on_signature_copy(src, dst, *args, **kwargs):
        if str(dst).endswith("slot.signature.json"):
            raise OSError("copy failed")
        return original_copyfile(src, dst, *args, **kwargs)

    monkeypatch.setattr(slot_install_module.shutil, "copyfile", fail_on_signature_copy)

    with pytest.raises(OSError, match="copy failed"):
        SlotInstaller().install(
            source_dir,
            install_dir=install_dir,
            policy=SlotInstallPolicy(trusted_signers=("ops",)),
        )

    assert not (install_dir / "local_rollback").exists()
    assert not (install_dir / ".local_rollback.stage").exists()


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
    key = _write_signature(manifest_path, key_id="ops-key")

    with pytest.raises(SlotConfigurationError, match="not enterprise allowlisted"):
        SlotInstaller().install(
            source_dir,
            install_dir=tmp_path / "installed",
            policy=SlotInstallPolicy(
                auth_mode="enterprise",
                trusted_publisher_keys={"ops-key": key["public_key"]},
            ),
        )

    result = SlotInstaller().install(
        source_dir,
        install_dir=tmp_path / "installed",
        policy=SlotInstallPolicy(
            auth_mode="enterprise",
            enterprise_allowlist=("local.signed",),
            trusted_publisher_keys={"ops-key": key["public_key"]},
        ),
    )

    assert result.status == "installed"
    assert result.signature.status == "verified"
    assert result.signature.key_id == "ops-key"
    assert result.signature.algorithm == "ed25519"
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


def test_valid_ed25519_signature_reports_verified_status(tmp_path) -> None:
    manifest_path = tmp_path / "slot.json"
    manifest_path.write_text(json.dumps(_manifest("local.verified")), encoding="utf-8")
    key = _write_signature(manifest_path, key_id="ops-key")

    signature = verify_slot_signature(
        manifest_path,
        slot_id="local.verified",
        trusted_publisher_keys={"ops-key": key["public_key"]},
    )

    assert signature.status == "verified"
    assert signature.verified is True
    assert signature.signer == "ops-key"
    assert signature.key_id == "ops-key"
    assert signature.algorithm == "ed25519"
    assert signature.manifest_sha256


def test_v3_signature_binds_package_digest_and_install_copies_package(tmp_path) -> None:
    source_dir = tmp_path / "signed_package"
    source_dir.mkdir()
    manifest_path = source_dir / "slot.json"
    manifest_path.write_text(json.dumps(_manifest("local.package")), encoding="utf-8")
    package_dir = _write_package(source_dir)
    key = _write_signature(manifest_path, key_id="ops-key", package_dir=package_dir)

    signature = verify_slot_signature(
        manifest_path,
        slot_id="local.package",
        trusted_publisher_keys={"ops-key": key["public_key"]},
    )
    result = SlotInstaller().install(
        source_dir,
        install_dir=tmp_path / "installed",
        policy=SlotInstallPolicy(trusted_publisher_keys={"ops-key": key["public_key"]}),
    )

    assert signature.status == "verified"
    assert signature.package_digest == package_tree_digest(package_dir)
    assert signature.package_digest["algorithm"] == "sha256_tree_v1"
    assert result.signature.package_digest == signature.package_digest
    assert (tmp_path / "installed" / "local_package" / "package" / "local_package" / "provider.py").exists()


def test_tampered_package_rejects_v3_signature(tmp_path) -> None:
    source_dir = tmp_path / "signed_package"
    source_dir.mkdir()
    manifest_path = source_dir / "slot.json"
    manifest_path.write_text(json.dumps(_manifest("local.tampered-package")), encoding="utf-8")
    package_dir = _write_package(source_dir)
    key = _write_signature(manifest_path, key_id="ops-key", package_dir=package_dir)
    (package_dir / "local_package" / "provider.py").write_text("tampered = True\n", encoding="utf-8")

    signature = verify_slot_signature(
        manifest_path,
        slot_id="local.tampered-package",
        trusted_publisher_keys={"ops-key": key["public_key"]},
    )

    assert signature.status == "invalid"
    assert "package digest mismatch" in signature.reason
    with pytest.raises(SlotConfigurationError, match="invalid signature"):
        SlotInstaller().install(
            source_dir,
            install_dir=tmp_path / "installed",
            policy=SlotInstallPolicy(trusted_publisher_keys={"ops-key": key["public_key"]}),
        )


def test_v3_signature_requires_manifest_sibling_package_dir(tmp_path) -> None:
    source_dir = tmp_path / "signed_package"
    source_dir.mkdir()
    manifest_path = source_dir / "slot.json"
    manifest_path.write_text(json.dumps(_manifest("local.external-package")), encoding="utf-8")
    external_package_dir = _write_package(tmp_path / "external")
    private_key = Ed25519PrivateKey.generate()
    private_key_path = source_dir / "ops-key.pem"
    private_key_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )

    with pytest.raises(SlotConfigurationError, match="beside the slot manifest"):
        sign_slot_manifest(
            manifest_path,
            private_key_path=private_key_path,
            key_id="ops-key",
            package_dir=external_package_dir,
        )


def test_untrusted_ed25519_signature_reports_untrusted_status(tmp_path) -> None:
    manifest_path = tmp_path / "slot.json"
    manifest_path.write_text(json.dumps(_manifest("local.untrusted")), encoding="utf-8")
    _write_signature(manifest_path, key_id="someone")

    signature = verify_slot_signature(
        manifest_path,
        slot_id="local.untrusted",
        trusted_publisher_keys={},
    )

    assert signature.status == "untrusted"
    assert signature.signer == "someone"
    assert signature.key_id == "someone"


def test_tampered_manifest_rejects_ed25519_signature(tmp_path) -> None:
    manifest_path = tmp_path / "slot.json"
    manifest_path.write_text(json.dumps(_manifest("local.tampered")), encoding="utf-8")
    key = _write_signature(manifest_path, key_id="ops-key")
    payload = _manifest("local.tampered")
    payload["version"] = "0.2.0"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    signature = verify_slot_signature(
        manifest_path,
        slot_id="local.tampered",
        trusted_publisher_keys={"ops-key": key["public_key"]},
    )

    assert signature.status == "invalid"
    assert "manifest hash mismatch" in signature.reason


def test_tampered_ed25519_signature_is_invalid(tmp_path) -> None:
    manifest_path = tmp_path / "slot.json"
    manifest_path.write_text(json.dumps(_manifest("local.bad_sig")), encoding="utf-8")
    key = _write_signature(manifest_path, key_id="ops-key")
    signature_path = manifest_path.parent / "slot.signature.json"
    sidecar = json.loads(signature_path.read_text(encoding="utf-8"))
    sidecar["signature"] = base64.b64encode(b"x" * 64).decode("ascii")
    signature_path.write_text(json.dumps(sidecar), encoding="utf-8")

    signature = verify_slot_signature(
        manifest_path,
        slot_id="local.bad_sig",
        trusted_publisher_keys={"ops-key": key["public_key"]},
    )

    assert signature.status == "invalid"
    assert "signature verification failed" in signature.reason


def test_revoked_ed25519_key_is_rejected(tmp_path) -> None:
    manifest_path = tmp_path / "slot.json"
    manifest_path.write_text(json.dumps(_manifest("local.revoked")), encoding="utf-8")
    key = _write_signature(manifest_path, key_id="ops-key")

    signature = verify_slot_signature(
        manifest_path,
        slot_id="local.revoked",
        trusted_publisher_keys={"ops-key": key["public_key"]},
        signing_repository=_RevokedSigningRepository(),
    )

    assert signature.status == "revoked"
    assert signature.revocation_checked is True
    with pytest.raises(SlotConfigurationError, match="signing key is revoked"):
        SlotInstaller().install(
            manifest_path,
            install_dir=tmp_path / "installed",
            policy=SlotInstallPolicy(
                trusted_publisher_keys={"ops-key": key["public_key"]},
                signing_repository=_RevokedSigningRepository(),
            ),
        )


def test_legacy_v1_signature_reports_legacy_status(tmp_path) -> None:
    manifest_path = tmp_path / "slot.json"
    manifest_path.write_text(json.dumps(_manifest("local.legacy")), encoding="utf-8")
    _write_legacy_signature(manifest_path, "local.legacy", signer="ops")

    result = SlotInstaller().install(
        manifest_path,
        install_dir=tmp_path / "installed",
        policy=SlotInstallPolicy(trusted_signers=("ops",)),
    )

    assert result.signature.status == "legacy"
    assert result.signature.verified is False
    assert result.warnings == ("legacy metadata signature, not cryptographic",)


class _RevokedSigningRepository:
    def is_revoked(self, key_id: str) -> bool:
        return True


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


def _write_signature(manifest_path, *, key_id: str, package_dir=None) -> dict[str, str]:
    private_key = Ed25519PrivateKey.generate()
    private_key_path = manifest_path.parent / f"{key_id}.pem"
    private_key_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    sign_slot_manifest(
        manifest_path,
        private_key_path=private_key_path,
        key_id=key_id,
        package_dir=package_dir,
    )
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return {"public_key": base64.b64encode(public_key).decode("ascii")}


def _write_package(source_dir) -> Path:
    package_dir = source_dir / "package"
    module_dir = package_dir / "local_package"
    module_dir.mkdir(parents=True)
    (module_dir / "__init__.py").write_text("", encoding="utf-8")
    (module_dir / "provider.py").write_text("VALUE = 'signed-package'\n", encoding="utf-8")
    return package_dir


def _write_legacy_signature(manifest_path, slot_id: str, *, signer: str) -> None:
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

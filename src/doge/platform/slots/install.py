"""Local third-party slot install preview.

Sprint 047 intentionally installs validated manifests only. It never imports a
slot provider entrypoint or executes third-party Python code.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from doge.platform.slots.errors import SlotConfigurationError
from doge.platform.slots.loader import SlotLoader
from doge.platform.slots.manifest import SlotManifest


@dataclass(frozen=True)
class SlotInstallPolicy:
    """Policy for local manifest install preview."""

    auth_mode: str = "local_demo"
    allow_unsigned_local: bool = True
    enterprise_allowlist: tuple[str, ...] = ()
    trusted_signers: tuple[str, ...] = ()
    trusted_publisher_keys: Mapping[str, str] = field(default_factory=dict)
    signing_repository: Any | None = None
    allow_high_risk: bool = False
    allow_shell: bool = False

    @property
    def enterprise(self) -> bool:
        return self.auth_mode == "enterprise"


@dataclass(frozen=True)
class SlotSignatureVerification:
    """Result of sidecar signature validation."""

    status: str
    signer: str = ""
    key_id: str = ""
    algorithm: str = ""
    manifest_sha256: str = ""
    package_digest: Mapping[str, Any] | None = None
    signature_path: Path | None = None
    reason: str = ""
    revocation_checked: bool = False

    @property
    def verified(self) -> bool:
        return self.status == "verified"


@dataclass(frozen=True)
class SlotInstallResult:
    """Safe install result for CLI/API surfaces."""

    slot_id: str
    status: str
    installed_path: Path
    source_path: Path
    signature: SlotSignatureVerification
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot_id": self.slot_id,
            "status": self.status,
            "installed_path": str(self.installed_path),
            "source_path": str(self.source_path),
            "signature": {
                "status": self.signature.status,
                "signer": self.signature.signer,
                "key_id": self.signature.key_id,
                "algorithm": self.signature.algorithm,
                "manifest_sha256": self.signature.manifest_sha256,
                "package_digest": dict(self.signature.package_digest)
                if self.signature.package_digest is not None
                else None,
                "signature_path": str(self.signature.signature_path)
                if self.signature.signature_path is not None
                else "",
                "reason": self.signature.reason,
                "revocation_checked": self.signature.revocation_checked,
            },
            "warnings": list(self.warnings),
        }


class SlotInstaller:
    """Validate and copy a manifest into the configured local slot directory."""

    def install(
        self,
        source: str | Path,
        *,
        install_dir: str | Path,
        policy: SlotInstallPolicy | None = None,
    ) -> SlotInstallResult:
        resolved_policy = policy or SlotInstallPolicy()
        manifest_path, manifest = inspect_slot_install_source(source)
        signature = verify_slot_signature(
            manifest_path,
            slot_id=manifest.id,
            trusted_signers=resolved_policy.trusted_signers,
            trusted_publisher_keys=resolved_policy.trusted_publisher_keys,
            signing_repository=resolved_policy.signing_repository,
        )
        warnings = _validate_install_policy(manifest, signature, resolved_policy)

        destination_dir = Path(install_dir) / _slot_dir_name(manifest.id)
        destination_path = destination_dir / "slot.json"
        status = "installed"
        source_digest = _manifest_sha256(manifest_path)
        if destination_path.exists():
            if _manifest_sha256(destination_path) != source_digest:
                raise SlotConfigurationError(
                    f"installed slot manifest already exists with different content: {manifest.id}"
                )
            status = "already_installed"
        else:
            destination_dir.parent.mkdir(parents=True, exist_ok=True)
            stage_dir = _stage_dir_for(destination_dir)
            if stage_dir.exists():
                shutil.rmtree(stage_dir)
            try:
                stage_dir.mkdir(parents=True)
                shutil.copyfile(manifest_path, stage_dir / "slot.json")
                if signature.signature_path is not None and signature.status in {"verified", "untrusted", "legacy"}:
                    shutil.copyfile(signature.signature_path, stage_dir / "slot.signature.json")
                if signature.package_digest is not None and signature.status in {"verified", "untrusted"}:
                    _copy_verified_package(manifest_path.parent / "package", stage_dir / "package", signature)
                stage_dir.replace(destination_dir)
            except Exception:
                if stage_dir.exists():
                    shutil.rmtree(stage_dir, ignore_errors=True)
                raise

        if status == "already_installed":
            if signature.signature_path is not None and signature.status in {"verified", "untrusted", "legacy"}:
                shutil.copyfile(signature.signature_path, destination_dir / "slot.signature.json")
            if signature.package_digest is not None and signature.status in {"verified", "untrusted"}:
                _copy_verified_package(manifest_path.parent / "package", destination_dir / "package", signature)

        return SlotInstallResult(
            slot_id=manifest.id,
            status=status,
            installed_path=destination_path,
            source_path=manifest_path,
            signature=signature,
            warnings=tuple(warnings),
        )


def inspect_slot_install_source(source: str | Path) -> tuple[Path, SlotManifest]:
    """Return the canonical manifest path and validated manifest for an install source."""

    manifest_path = _manifest_path_from_source(source)
    [slot] = SlotLoader().load([manifest_path])
    return manifest_path, slot.manifest()


def verify_slot_signature(
    manifest_path: str | Path,
    *,
    slot_id: str,
    trusted_signers: tuple[str, ...] = (),
    trusted_publisher_keys: Mapping[str, str] | None = None,
    signing_repository: Any | None = None,
) -> SlotSignatureVerification:
    """Validate optional sidecar signature metadata or Ed25519 signatures."""

    path = _signature_path_for(Path(manifest_path))
    if not path.exists():
        return SlotSignatureVerification("missing", signature_path=path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return SlotSignatureVerification("invalid", signature_path=path, reason=str(exc))
    if not isinstance(raw, dict):
        return SlotSignatureVerification(
            "invalid",
            signature_path=path,
            reason="signature must be a JSON object",
        )
    schema_version = raw.get("schema_version")
    if schema_version == 1:
        return _verify_legacy_signature_metadata(
            Path(manifest_path),
            slot_id=slot_id,
            raw=raw,
            path=path,
            trusted_signers=trusted_signers,
        )
    if schema_version not in {2, 3}:
        return SlotSignatureVerification(
            "invalid",
            signature_path=path,
            reason="schema_version must be 1, 2, or 3",
        )

    key_id = raw.get("key_id")
    algorithm = raw.get("algorithm")
    signature = raw.get("signature")
    manifest_sha256 = raw.get("manifest_sha256")
    if raw.get("slot_id") != slot_id:
        return SlotSignatureVerification(
            "invalid",
            key_id=str(key_id or ""),
            algorithm=str(algorithm or ""),
            signature_path=path,
            reason="slot_id mismatch",
        )
    if not isinstance(key_id, str) or not key_id.strip():
        return SlotSignatureVerification("invalid", signature_path=path, reason="key_id is required")
    key_id = key_id.strip()
    if algorithm != "ed25519":
        return SlotSignatureVerification(
            "invalid",
            key_id=key_id,
            algorithm=str(algorithm or ""),
            signature_path=path,
            reason="algorithm must be ed25519",
        )
    if not isinstance(signature, str) or not signature.strip():
        return SlotSignatureVerification(
            "invalid",
            key_id=key_id,
            algorithm=algorithm,
            signature_path=path,
            reason="signature is required",
        )
    try:
        canonical_bytes = canonical_manifest_bytes(manifest_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return SlotSignatureVerification(
            "invalid",
            key_id=key_id,
            algorithm=algorithm,
            signature_path=path,
            reason=f"manifest canonicalization failed: {exc}",
        )
    expected_sha256 = hashlib.sha256(canonical_bytes).hexdigest()
    if manifest_sha256 != expected_sha256:
        return SlotSignatureVerification(
            "invalid",
            key_id=key_id,
            algorithm=algorithm,
            manifest_sha256=str(manifest_sha256 or ""),
            signature_path=path,
            reason="manifest hash mismatch",
        )
    package_digest: Mapping[str, Any] | None = None
    signature_payload = canonical_bytes
    if schema_version == 3:
        declared_digest = raw.get("package_digest")
        if not isinstance(declared_digest, dict):
            return SlotSignatureVerification(
                "invalid",
                key_id=key_id,
                algorithm=algorithm,
                manifest_sha256=expected_sha256,
                signature_path=path,
                reason="package_digest is required for schema_version 3",
            )
        try:
            package_digest = package_tree_digest(Path(manifest_path).parent / "package")
        except (OSError, ValueError, SlotConfigurationError) as exc:
            return SlotSignatureVerification(
                "invalid",
                key_id=key_id,
                algorithm=algorithm,
                manifest_sha256=expected_sha256,
                signature_path=path,
                reason=f"package digest failed: {exc}",
            )
        try:
            declared_digest_bytes = _canonical_package_digest(declared_digest)
            computed_digest_bytes = _canonical_package_digest(package_digest)
        except SlotConfigurationError as exc:
            return SlotSignatureVerification(
                "invalid",
                key_id=key_id,
                algorithm=algorithm,
                manifest_sha256=expected_sha256,
                package_digest=dict(declared_digest),
                signature_path=path,
                reason=str(exc),
            )
        if declared_digest_bytes != computed_digest_bytes:
            return SlotSignatureVerification(
                "invalid",
                key_id=key_id,
                algorithm=algorithm,
                manifest_sha256=expected_sha256,
                package_digest=dict(declared_digest),
                signature_path=path,
                reason="package digest mismatch",
            )
        signature_payload = canonical_bytes + computed_digest_bytes

    keys = trusted_publisher_keys or {}
    encoded_public_key = keys.get(key_id)
    if not encoded_public_key:
        return SlotSignatureVerification(
            "untrusted",
            key_id=key_id,
            signer=key_id,
            algorithm=algorithm,
            manifest_sha256=expected_sha256,
            package_digest=package_digest,
            signature_path=path,
            reason="key_id is not trusted",
        )
    revocation_checked = signing_repository is not None
    if signing_repository is not None and signing_repository.is_revoked(key_id):
        return SlotSignatureVerification(
            "revoked",
            key_id=key_id,
            signer=key_id,
            algorithm=algorithm,
            manifest_sha256=expected_sha256,
            package_digest=package_digest,
            signature_path=path,
            reason="key_id is revoked",
            revocation_checked=True,
        )
    try:
        public_key = Ed25519PublicKey.from_public_bytes(_b64decode(encoded_public_key))
        public_key.verify(_b64decode(signature), signature_payload)
    except (ValueError, binascii.Error, InvalidSignature) as exc:
        return SlotSignatureVerification(
            "invalid",
            key_id=key_id,
            signer=key_id,
            algorithm=algorithm,
            manifest_sha256=expected_sha256,
            package_digest=package_digest,
            signature_path=path,
            reason=f"signature verification failed: {exc}",
            revocation_checked=revocation_checked,
        )
    return SlotSignatureVerification(
        "verified",
        key_id=key_id,
        signer=key_id,
        algorithm=algorithm,
        manifest_sha256=expected_sha256,
        package_digest=package_digest,
        signature_path=path,
        revocation_checked=revocation_checked,
    )


def sign_slot_manifest(
    manifest_path: str | Path,
    *,
    private_key_path: str | Path,
    key_id: str,
    package_dir: str | Path | None = None,
    password: bytes | None = None,
) -> dict[str, Any]:
    """Write an Ed25519 slot signature sidecar for ``manifest_path``."""

    key_id = key_id.strip()
    if not key_id:
        raise SlotConfigurationError("key_id is required")
    manifest = _manifest_json(Path(manifest_path))
    slot_id = manifest.get("id")
    if not isinstance(slot_id, str) or not slot_id:
        raise SlotConfigurationError("slot manifest id is required")
    key = serialization.load_pem_private_key(Path(private_key_path).read_bytes(), password=password)
    if not isinstance(key, Ed25519PrivateKey):
        raise SlotConfigurationError("slot signing key must be an Ed25519 private key")
    canonical_bytes = _canonical_manifest_bytes_from_obj(manifest)
    package_digest = None
    signature_payload = canonical_bytes
    schema_version = 2
    if package_dir is not None:
        expected_package_dir = Path(manifest_path).parent / "package"
        package_path = Path(package_dir)
        if package_path.resolve() != expected_package_dir.resolve():
            raise SlotConfigurationError(
                "package_dir must be the package directory beside the slot manifest"
            )
        package_digest = package_tree_digest(package_path)
        signature_payload = canonical_bytes + _canonical_package_digest(package_digest)
        schema_version = 3
    signature = key.sign(signature_payload)
    payload = {
        "schema_version": schema_version,
        "slot_id": slot_id,
        "key_id": key_id,
        "algorithm": "ed25519",
        "signature": base64.b64encode(signature).decode("ascii"),
        "manifest_sha256": hashlib.sha256(canonical_bytes).hexdigest(),
    }
    if package_digest is not None:
        payload["package_digest"] = package_digest
    signature_path = _signature_path_for(Path(manifest_path))
    signature_path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "status": "signed",
        "slot_id": slot_id,
        "key_id": key_id,
        "algorithm": "ed25519",
        "signature_path": str(signature_path),
        "manifest_sha256": payload["manifest_sha256"],
        "schema_version": schema_version,
        "package_digest": package_digest,
    }


def _validate_install_policy(
    manifest: SlotManifest,
    signature: SlotSignatureVerification,
    policy: SlotInstallPolicy,
) -> list[str]:
    warnings: list[str] = []
    permissions = manifest.permissions
    if permissions.risk_level == "forbidden":
        raise SlotConfigurationError(f"slot {manifest.id} declares forbidden risk")
    if permissions.risk_level == "high" and not policy.allow_high_risk:
        raise SlotConfigurationError(f"slot {manifest.id} declares high risk")
    if permissions.shell == "allow" and not policy.allow_shell:
        raise SlotConfigurationError(f"slot {manifest.id} declares shell permission")
    if signature.status == "invalid":
        raise SlotConfigurationError(
            f"slot {manifest.id} has invalid signature: {signature.reason}"
        )
    if signature.status == "revoked":
        raise SlotConfigurationError(f"slot {manifest.id} signing key is revoked")
    if policy.enterprise:
        if manifest.id not in policy.enterprise_allowlist:
            raise SlotConfigurationError(f"slot {manifest.id} is not enterprise allowlisted")
        if not policy.trusted_publisher_keys:
            raise SlotConfigurationError("enterprise slot install requires trusted publisher keys")
        if not signature.verified:
            raise SlotConfigurationError(
                f"slot {manifest.id} requires verified cryptographic signature in enterprise mode"
            )
        return warnings
    if signature.status == "missing":
        if not policy.allow_unsigned_local:
            raise SlotConfigurationError(f"slot {manifest.id} is unsigned")
        warnings.append("unsigned local slot manifest")
    elif signature.status == "untrusted":
        warnings.append("slot signature key_id is not trusted")
    elif signature.status == "legacy":
        warnings.append("legacy metadata signature, not cryptographic")
    return warnings


def _manifest_path_from_source(source: str | Path) -> Path:
    path = Path(source)
    if path.is_file():
        return path
    if not path.exists():
        raise SlotConfigurationError(f"slot install source does not exist: {path}")
    if not path.is_dir():
        raise SlotConfigurationError(f"slot install source is not a file or directory: {path}")
    manifest_path = path / "slot.json"
    if not manifest_path.is_file():
        raise SlotConfigurationError(f"slot install directory must contain slot.json: {path}")
    return manifest_path


def _stage_dir_for(destination_dir: Path) -> Path:
    return destination_dir.with_name(f".{destination_dir.name}.stage")


def _signature_path_for(manifest_path: Path) -> Path:
    if manifest_path.name == "slot.json":
        return manifest_path.with_name("slot.signature.json")
    return manifest_path.with_suffix(".signature.json")


def _verify_legacy_signature_metadata(
    manifest_path: Path,
    *,
    slot_id: str,
    raw: dict[str, Any],
    path: Path,
    trusted_signers: tuple[str, ...],
) -> SlotSignatureVerification:
    signer = raw.get("signer")
    if not isinstance(signer, str) or not signer.strip():
        return SlotSignatureVerification("invalid", signature_path=path, reason="signer is required")
    if raw.get("slot_id") != slot_id:
        return SlotSignatureVerification(
            "invalid",
            signer=signer,
            signature_path=path,
            reason="slot_id mismatch",
        )
    manifest_sha256 = _raw_sha256_file(manifest_path)
    if raw.get("manifest_sha256") != manifest_sha256:
        return SlotSignatureVerification(
            "invalid",
            signer=signer,
            manifest_sha256=str(raw.get("manifest_sha256") or ""),
            signature_path=path,
            reason="manifest hash mismatch",
        )
    if trusted_signers and signer not in trusted_signers:
        return SlotSignatureVerification(
            "untrusted",
            signer=signer,
            signature_path=path,
            reason="legacy signer is not trusted",
        )
    return SlotSignatureVerification(
        "legacy",
        signer=signer,
        signature_path=path,
        manifest_sha256=manifest_sha256,
        reason="legacy metadata signature is not cryptographic",
    )


def canonical_manifest_bytes(path: str | Path) -> bytes:
    """Return canonical JSON bytes for a slot manifest file."""

    return _canonical_manifest_bytes_from_obj(_manifest_json(Path(path)))


def package_tree_digest(package_dir: str | Path) -> dict[str, Any]:
    """Return the deterministic SHA-256 tree digest for a provider package dir."""

    root = Path(package_dir)
    if not root.exists():
        raise SlotConfigurationError(f"slot provider package directory does not exist: {root}")
    if not root.is_dir():
        raise SlotConfigurationError(f"slot provider package path is not a directory: {root}")
    root_resolved = root.resolve()
    entries: list[dict[str, str]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink():
            raise SlotConfigurationError(f"slot provider package cannot contain symlink: {path}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise SlotConfigurationError(f"slot provider package contains non-file path: {path}")
        resolved = path.resolve()
        try:
            relative = resolved.relative_to(root_resolved)
        except ValueError as exc:
            raise SlotConfigurationError(f"slot provider package path escapes package dir: {path}") from exc
        entries.append(
            {
                "path": relative.as_posix(),
                "sha256": _raw_sha256_file(path),
            }
        )
    if not entries:
        raise SlotConfigurationError("slot provider package directory is empty")
    digest_payload = json.dumps(
        entries,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return {
        "algorithm": "sha256_tree_v1",
        "layout": "directory",
        "file_count": len(entries),
        "value": hashlib.sha256(digest_payload).hexdigest(),
    }


def _manifest_json(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("slot manifest must be a JSON object")
    return raw


def _canonical_manifest_bytes_from_obj(manifest: dict[str, Any]) -> bytes:
    return json.dumps(
        manifest,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _manifest_sha256(path: Path) -> str:
    return hashlib.sha256(canonical_manifest_bytes(path)).hexdigest()


def _raw_sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_package_digest(package_digest: Mapping[str, Any]) -> bytes:
    try:
        normalized = {
            "algorithm": package_digest["algorithm"],
            "file_count": package_digest["file_count"],
            "layout": package_digest["layout"],
            "value": package_digest["value"],
        }
    except KeyError as exc:
        raise SlotConfigurationError(f"package_digest missing {exc.args[0]}") from exc
    if normalized["algorithm"] != "sha256_tree_v1":
        raise SlotConfigurationError("package_digest.algorithm must be sha256_tree_v1")
    if normalized["layout"] != "directory":
        raise SlotConfigurationError("package_digest.layout must be directory")
    if not isinstance(normalized["file_count"], int) or normalized["file_count"] <= 0:
        raise SlotConfigurationError("package_digest.file_count must be a positive integer")
    if not isinstance(normalized["value"], str) or len(normalized["value"]) != 64:
        raise SlotConfigurationError("package_digest.value must be a sha256 hex digest")
    return json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _copy_verified_package(
    source_package_dir: Path,
    destination_package_dir: Path,
    signature: SlotSignatureVerification,
) -> None:
    if signature.package_digest is None:
        return
    source_digest = package_tree_digest(source_package_dir)
    if _canonical_package_digest(source_digest) != _canonical_package_digest(signature.package_digest):
        raise SlotConfigurationError("slot provider package digest changed before install copy")
    if destination_package_dir.exists():
        destination_digest = package_tree_digest(destination_package_dir)
        if _canonical_package_digest(destination_digest) != _canonical_package_digest(signature.package_digest):
            raise SlotConfigurationError("installed slot provider package already exists with different content")
        return
    shutil.copytree(source_package_dir, destination_package_dir)


def _b64decode(value: str) -> bytes:
    return base64.b64decode(value.encode("ascii"), validate=True)


def _slot_dir_name(slot_id: str) -> str:
    return slot_id.replace(".", "_").replace("-", "_")

"""Local third-party slot install preview.

Sprint 047 intentionally installs validated manifests only. It never imports a
slot provider entrypoint or executes third-party Python code.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
    allow_high_risk: bool = False
    allow_shell: bool = False

    @property
    def enterprise(self) -> bool:
        return self.auth_mode == "enterprise"


@dataclass(frozen=True)
class SlotSignatureVerification:
    """Result of sidecar signature metadata validation."""

    status: str
    signer: str = ""
    signature_path: Path | None = None
    reason: str = ""

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
                "signature_path": str(self.signature.signature_path)
                if self.signature.signature_path is not None
                else "",
                "reason": self.signature.reason,
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
        manifest_path = _manifest_path_from_source(source)
        [slot] = SlotLoader().load([manifest_path])
        manifest = slot.manifest()
        signature = verify_slot_signature(
            manifest_path,
            slot_id=manifest.id,
            trusted_signers=resolved_policy.trusted_signers,
        )
        warnings = _validate_install_policy(manifest, signature, resolved_policy)

        destination_dir = Path(install_dir) / _slot_dir_name(manifest.id)
        destination_path = destination_dir / "slot.json"
        status = "installed"
        source_digest = _sha256_file(manifest_path)
        if destination_path.exists():
            if _sha256_file(destination_path) != source_digest:
                raise SlotConfigurationError(
                    f"installed slot manifest already exists with different content: {manifest.id}"
                )
            status = "already_installed"
        else:
            destination_dir.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(manifest_path, destination_path)

        if signature.signature_path is not None and signature.status in {"verified", "untrusted"}:
            shutil.copyfile(signature.signature_path, destination_dir / "slot.signature.json")

        return SlotInstallResult(
            slot_id=manifest.id,
            status=status,
            installed_path=destination_path,
            source_path=manifest_path,
            signature=signature,
            warnings=tuple(warnings),
        )


def verify_slot_signature(
    manifest_path: str | Path,
    *,
    slot_id: str,
    trusted_signers: tuple[str, ...] = (),
) -> SlotSignatureVerification:
    """Validate optional sidecar signature metadata.

    The sidecar is a local-alpha metadata proof:
    ``{"schema_version": 1, "slot_id": "...", "manifest_sha256": "...", "signer": "..."}``.
    It is not a cryptographic signature format.
    """

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
    if raw.get("schema_version") != 1:
        return SlotSignatureVerification(
            "invalid",
            signature_path=path,
            reason="schema_version must be 1",
        )
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
    if raw.get("manifest_sha256") != _sha256_file(Path(manifest_path)):
        return SlotSignatureVerification(
            "invalid",
            signer=signer,
            signature_path=path,
            reason="manifest hash mismatch",
        )
    if signer not in trusted_signers:
        return SlotSignatureVerification(
            "untrusted",
            signer=signer,
            signature_path=path,
            reason="signer is not trusted",
        )
    return SlotSignatureVerification("verified", signer=signer, signature_path=path)


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
            f"slot {manifest.id} has invalid signature metadata: {signature.reason}"
        )
    if policy.enterprise:
        if manifest.id not in policy.enterprise_allowlist:
            raise SlotConfigurationError(f"slot {manifest.id} is not enterprise allowlisted")
        if not policy.trusted_signers:
            raise SlotConfigurationError("enterprise slot install requires trusted signers")
        if not signature.verified:
            raise SlotConfigurationError(
                f"slot {manifest.id} requires verified signature in enterprise mode"
            )
        return warnings
    if signature.status == "missing":
        if not policy.allow_unsigned_local:
            raise SlotConfigurationError(f"slot {manifest.id} is unsigned")
        warnings.append("unsigned local slot manifest")
    elif signature.status == "untrusted":
        warnings.append("slot signature signer is not trusted")
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


def _signature_path_for(manifest_path: Path) -> Path:
    if manifest_path.name == "slot.json":
        return manifest_path.with_name("slot.signature.json")
    return manifest_path.with_suffix(".signature.json")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _slot_dir_name(slot_id: str) -> str:
    return slot_id.replace(".", "_").replace("-", "_")

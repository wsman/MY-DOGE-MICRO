"""Bootstrap-owned installed provider slot execution path.

The pure :mod:`doge.platform.slots` package intentionally keeps disk manifests
manifest-only. P5's importlib execution path needs settings, signature trust,
revocation storage, and runtime permission guards, so it belongs in bootstrap.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from doge.platform.slots import (
    ISlot,
    SlotConfigurationError,
    SlotContribution,
    SlotContext,
    SlotManifest,
    SlotSignatureVerification,
    SlotType,
    slot_permission_context,
    verify_slot_signature,
)

_EXECUTABLE_TYPES = frozenset(
    {
        SlotType.TOOL,
        SlotType.MODEL,
        SlotType.WORKFLOW,
        SlotType.DATA,
        SlotType.DOCUMENT,
    }
)

_TYPE_FACETS = {
    SlotType.TOOL: ("tools",),
    SlotType.MODEL: ("model_backends",),
    SlotType.WORKFLOW: ("workflows",),
    SlotType.DATA: ("data_sources",),
    SlotType.DOCUMENT: ("document_parsers",),
}

_RESTRICTED_FACETS = (
    "routes",
    "ui_panels",
    "watchers",
    "eval_suites",
    "governance_policies",
)


@dataclass(frozen=True)
class ProviderExecutionDecision:
    """Provider execution eligibility result for status and resolve gates."""

    eligible: bool
    blockers: tuple[str, ...]
    signature: SlotSignatureVerification | None = None
    mode: str = "provider_execution"
    installed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "installed": self.installed,
            "eligible": self.eligible,
            "blockers": list(self.blockers),
            "signature": _signature_dict(self.signature),
        }


@dataclass
class InstalledProviderSlot(ISlot):
    """Installed, signed slot whose provider entrypoint may execute after P5 gates."""

    slot_manifest: SlotManifest
    source_path: Path
    settings: Any
    trusted_publisher_keys: Mapping[str, str]
    signing_repository: Any
    _provider: ISlot | None = field(default=None, init=False, repr=False)

    def manifest(self) -> SlotManifest:
        return self.slot_manifest

    def resolve(self, context: SlotContext) -> SlotContribution:
        decision = provider_execution_decision(
            self.slot_manifest,
            self.source_path,
            self.settings,
            trusted_publisher_keys=self.trusted_publisher_keys,
            signing_repository=self.signing_repository,
            admission_status="resolved",
            installed=True,
        )
        if not decision.eligible:
            raise SlotConfigurationError(
                f"slot {self.slot_manifest.id} is not eligible for provider execution: "
                + "; ".join(decision.blockers)
            )
        provider = self._load_provider(context)
        with slot_permission_context(
            self.slot_manifest.id,
            self.slot_manifest.permissions,
            enforce=bool(getattr(self.settings.features, "slot_runtime_interception", False)),
            audit_sink=None,
        ):
            contribution = provider.resolve(context)
        _validate_contribution(self.slot_manifest, contribution)
        return contribution

    def health(self, context: SlotContext):
        # Discovery/status must remain no-import. Provider health can execute
        # later once a hardened execution lifecycle exists.
        return self.slot_manifest.health

    def start(self, context: SlotContext) -> None:
        self._ensure_eligible()
        provider = self._load_provider(context)
        provider.start(context)

    def stop(self, context: SlotContext) -> None:
        self._ensure_eligible()
        provider = self._load_provider(context)
        provider.stop(context)

    def _ensure_eligible(self) -> None:
        decision = provider_execution_decision(
            self.slot_manifest,
            self.source_path,
            self.settings,
            trusted_publisher_keys=self.trusted_publisher_keys,
            signing_repository=self.signing_repository,
            admission_status="resolved",
            installed=True,
        )
        if not decision.eligible:
            raise SlotConfigurationError(
                f"slot {self.slot_manifest.id} is not eligible for provider execution: "
                + "; ".join(decision.blockers)
            )

    def _load_provider(self, context: SlotContext) -> ISlot:
        if self._provider is not None:
            return self._provider
        with slot_permission_context(
            self.slot_manifest.id,
            self.slot_manifest.permissions,
            enforce=bool(getattr(self.settings.features, "slot_runtime_interception", False)),
            audit_sink=None,
        ):
            provider = _import_provider(self.slot_manifest.entrypoint)
            _validate_provider_manifest(self.slot_manifest, provider.manifest())
        self._provider = provider
        return provider


def provider_execution_decision(
    manifest: SlotManifest,
    source_path: Path | None,
    settings: Any,
    *,
    trusted_publisher_keys: Mapping[str, str] | None = None,
    signing_repository: Any | None = None,
    admission_status: str | None = None,
    installed: bool,
) -> ProviderExecutionDecision:
    """Evaluate P5's execution gates without importing provider code."""

    blockers: list[str] = []
    features = settings.features
    if not bool(getattr(features, "slot_platform", False)):
        blockers.append("slot_platform disabled")
    if not bool(getattr(features, "slot_loader", False)):
        blockers.append("slot_loader disabled")
    if not bool(getattr(features, "slot_install", False)):
        blockers.append("slot_install disabled")
    if not installed:
        blockers.append("not installed slot")
    if manifest.type not in _EXECUTABLE_TYPES:
        blockers.append(f"slot type {manifest.type.value} is not provider-executable")
    if not bool(getattr(features, "slot_runtime_interception", False)):
        blockers.append("slot_runtime_interception disabled")
    if not bool(getattr(features, "slot_provider_execution", False)):
        blockers.append("slot_provider_execution disabled")
    if admission_status is not None and admission_status != "resolved":
        blockers.append("slot kernel admission disabled")

    if getattr(settings.auth, "mode", "local_demo") == "enterprise":
        allowlist = set(getattr(settings.slots, "enterprise_allowlist", ()))
        if manifest.id not in allowlist:
            blockers.append("slot is not enterprise allowlisted")

    signature = None
    trusted_keys = dict(trusted_publisher_keys or {})
    if not trusted_keys:
        blockers.append("no trusted publisher keys configured")
    if signing_repository is None:
        blockers.append("signing revocation repository unavailable")
    if source_path is None:
        blockers.append("installed manifest path unavailable")
    else:
        signature = verify_slot_signature(
            source_path,
            slot_id=manifest.id,
            trusted_publisher_keys=trusted_keys,
            signing_repository=signing_repository,
        )
        if not signature.verified:
            reason = f": {signature.reason}" if signature.reason else ""
            blockers.append(f"signature {signature.status}{reason}")
        elif not signature.revocation_checked:
            blockers.append("signing key revocation was not checked")

    return ProviderExecutionDecision(
        eligible=not blockers,
        blockers=tuple(blockers),
        signature=signature,
        installed=installed,
    )


def manifest_only_execution_decision(
    manifest: SlotManifest,
    *,
    source_path: Path | None,
    settings: Any,
    installed: bool,
    trusted_publisher_keys: Mapping[str, str] | None = None,
    signing_repository: Any | None = None,
    admission_status: str | None = None,
) -> ProviderExecutionDecision:
    decision = provider_execution_decision(
        manifest,
        source_path,
        settings,
        trusted_publisher_keys=trusted_publisher_keys,
        signing_repository=signing_repository,
        admission_status=admission_status,
        installed=installed,
    )
    blockers = ("manifest-only slot", *decision.blockers)
    return ProviderExecutionDecision(
        eligible=False,
        blockers=tuple(dict.fromkeys(blockers)),
        signature=decision.signature,
        mode="manifest_only",
        installed=installed,
    )


def builtin_execution_decision() -> ProviderExecutionDecision:
    return ProviderExecutionDecision(
        eligible=False,
        blockers=("built-in slot",),
        mode="builtin",
        installed=False,
    )


def _import_provider(entrypoint: str) -> ISlot:
    try:
        module_name, attr_name = entrypoint.rsplit(".", 1)
    except ValueError as exc:
        raise SlotConfigurationError(
            f"slot provider entrypoint must be a dotted object path: {entrypoint}"
        ) from exc
    try:
        module = importlib.import_module(module_name)
        target = getattr(module, attr_name)
    except Exception as exc:  # noqa: BLE001 - annotate entrypoint for operators
        raise SlotConfigurationError(f"failed to import slot provider {entrypoint}: {exc}") from exc
    provider = target() if callable(target) else target
    if not isinstance(provider, ISlot):
        raise SlotConfigurationError(
            f"slot provider {entrypoint} must instantiate doge.platform.slots.ISlot"
        )
    return provider


def _validate_provider_manifest(installed: SlotManifest, provided: SlotManifest) -> None:
    if provided.id != installed.id:
        raise SlotConfigurationError(
            f"slot provider manifest id mismatch: {provided.id!r} != {installed.id!r}"
        )
    if provided.type is not installed.type:
        raise SlotConfigurationError(
            f"slot provider manifest type mismatch: {provided.type.value!r} != {installed.type.value!r}"
        )
    if provided.provides != installed.provides:
        raise SlotConfigurationError(
            f"slot provider manifest provides mismatch for {installed.id}"
        )


def _validate_contribution(manifest: SlotManifest, contribution: SlotContribution) -> None:
    if contribution.slot_id != manifest.id:
        raise SlotConfigurationError(
            f"slot provider contribution id mismatch: {contribution.slot_id!r} != {manifest.id!r}"
        )
    for field_name in _RESTRICTED_FACETS:
        if getattr(contribution, field_name):
            raise SlotConfigurationError(
                f"slot {manifest.id} contributed restricted facet {field_name}"
            )
    allowed_facets = set(_TYPE_FACETS[manifest.type])
    for slot_type, facet_names in _TYPE_FACETS.items():
        if slot_type is manifest.type:
            continue
        for field_name in facet_names:
            if field_name not in allowed_facets and getattr(contribution, field_name):
                raise SlotConfigurationError(
                    f"slot {manifest.id} contributed facet {field_name} outside its type"
                )
    if manifest.type is SlotType.TOOL and manifest.provides.tools:
        names = tuple(tool.name for tool in contribution.tools)
        if names != manifest.provides.tools:
            raise SlotConfigurationError(
                f"slot {manifest.id} tool contribution does not match manifest provides.tools"
            )


def _signature_dict(signature: SlotSignatureVerification | None) -> dict[str, Any] | None:
    if signature is None:
        return None
    return {
        "status": signature.status,
        "signer": signature.signer,
        "key_id": signature.key_id,
        "algorithm": signature.algorithm,
        "manifest_sha256": signature.manifest_sha256,
        "signature_path": str(signature.signature_path) if signature.signature_path else "",
        "reason": signature.reason,
        "revocation_checked": signature.revocation_checked,
    }

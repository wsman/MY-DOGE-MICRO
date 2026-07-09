"""Bootstrap-owned installed provider slot execution path.

The pure :mod:`doge.platform.slots` package intentionally keeps disk manifests
manifest-only. P5's importlib execution path needs settings, signature trust,
revocation storage, and runtime permission guards, so it belongs in bootstrap.
"""

from __future__ import annotations

import importlib.util
import sys
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
        with self._permission_context():
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
        with self._permission_context():
            provider.start(context)

    def stop(self, context: SlotContext) -> None:
        self._ensure_eligible()
        provider = self._load_provider(context)
        with self._permission_context():
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
        with self._permission_context():
            provider = _import_provider(
                self.slot_manifest.entrypoint,
                package_dir=self.source_path.parent / "package",
            )
            _validate_provider_manifest(self.slot_manifest, provider.manifest())
        self._provider = provider
        return provider

    def _permission_context(self):
        return slot_permission_context(
            self.slot_manifest.id,
            self.slot_manifest.permissions,
            enforce=bool(getattr(self.settings.features, "slot_runtime_interception", False)),
            audit_sink=None,
        )


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
        elif signature.package_digest is None:
            blockers.append("signature is manifest-only; package signature required")
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


def _import_provider(entrypoint: str, *, package_dir: Path) -> ISlot:
    try:
        module_name, attr_name = entrypoint.rsplit(".", 1)
    except ValueError as exc:
        raise SlotConfigurationError(
            f"slot provider entrypoint must be a dotted object path: {entrypoint}"
        ) from exc
    try:
        module = _load_module_from_package(module_name, package_dir)
        target = getattr(module, attr_name)
    except Exception as exc:  # noqa: BLE001 - annotate entrypoint for operators
        raise SlotConfigurationError(f"failed to import slot provider {entrypoint}: {exc}") from exc
    provider = target() if callable(target) else target
    if not isinstance(provider, ISlot):
        raise SlotConfigurationError(
            f"slot provider {entrypoint} must instantiate doge.platform.slots.ISlot"
        )
    return provider


def _load_module_from_package(module_name: str, package_dir: Path):
    package_root = package_dir.resolve()
    if not package_root.is_dir():
        raise SlotConfigurationError(f"slot provider package directory is missing: {package_dir}")
    parts = module_name.split(".")
    if not all(parts):
        raise SlotConfigurationError(f"slot provider module path is invalid: {module_name}")
    if parts[0] == "doge":
        raise SlotConfigurationError("slot provider package name cannot shadow doge platform modules")
    _reject_host_root_collision(parts[0], package_root)
    _purge_package_prefix(parts[0])

    for index in range(1, len(parts)):
        package_name = ".".join(parts[:index])
        package_path = package_root.joinpath(*parts[:index])
        init_path = package_path / "__init__.py"
        if init_path.is_file():
            _load_module_from_file(
                package_name,
                init_path,
                package_root=package_root,
                submodule_search_locations=[str(package_path)],
            )

    module_file = package_root.joinpath(*parts).with_suffix(".py")
    package_init = package_root.joinpath(*parts, "__init__.py")
    if module_file.is_file():
        return _load_module_from_file(module_name, module_file, package_root=package_root)
    if package_init.is_file():
        package_path = package_init.parent
        return _load_module_from_file(
            module_name,
            package_init,
            package_root=package_root,
            submodule_search_locations=[str(package_path)],
        )
    raise SlotConfigurationError(
        f"slot provider module {module_name!r} is not inside signed package {package_dir}"
    )


def _purge_package_prefix(root_name: str) -> None:
    prefix = root_name + "."
    for module_name in sorted(
        (
            name
            for name in sys.modules
            if name == root_name or name.startswith(prefix)
        ),
        key=lambda name: name.count("."),
        reverse=True,
    ):
        sys.modules.pop(module_name, None)


def _reject_host_root_collision(root_name: str, package_root: Path) -> None:
    existing = sys.modules.get(root_name)
    if existing is not None:
        if _module_is_from_package(existing, package_root):
            return
        raise SlotConfigurationError(
            f"slot provider package root {root_name!r} collides with an already loaded host module"
        )
    try:
        spec = importlib.util.find_spec(root_name)
    except (ImportError, OSError, ValueError):
        return
    if spec is None:
        return
    if _spec_is_from_package(spec, package_root):
        return
    raise SlotConfigurationError(
        f"slot provider package root {root_name!r} collides with an importable host module"
    )


def _module_is_from_package(module: Any, package_root: Path) -> bool:
    candidates: list[Path] = []
    module_file = getattr(module, "__file__", None)
    if module_file:
        candidates.append(Path(str(module_file)))
    module_path = getattr(module, "__path__", None)
    if module_path:
        candidates.extend(Path(str(item)) for item in module_path)
    spec = getattr(module, "__spec__", None)
    origin = getattr(spec, "origin", None)
    if origin and origin not in {"built-in", "frozen", "namespace"}:
        candidates.append(Path(str(origin)))
    return _all_paths_are_from_package(candidates, package_root)


def _spec_is_from_package(spec: Any, package_root: Path) -> bool:
    candidates: list[Path] = []
    origin = getattr(spec, "origin", None)
    if origin and origin not in {"built-in", "frozen", "namespace"}:
        candidates.append(Path(str(origin)))
    locations = getattr(spec, "submodule_search_locations", None)
    if locations:
        candidates.extend(Path(str(item)) for item in locations)
    return _all_paths_are_from_package(candidates, package_root)


def _all_paths_are_from_package(candidates: list[Path], package_root: Path) -> bool:
    if not candidates:
        return False
    for candidate in candidates:
        try:
            candidate.resolve().relative_to(package_root)
        except (OSError, ValueError):
            return False
    return True


def _load_module_from_file(
    module_name: str,
    module_path: Path,
    *,
    package_root: Path,
    submodule_search_locations: list[str] | None = None,
):
    resolved = module_path.resolve()
    try:
        resolved.relative_to(package_root)
    except ValueError as exc:
        raise SlotConfigurationError(f"slot provider module escapes signed package: {module_path}") from exc
    spec = importlib.util.spec_from_file_location(
        module_name,
        resolved,
        submodule_search_locations=submodule_search_locations,
    )
    if spec is None or spec.loader is None:
        raise SlotConfigurationError(f"failed to build import spec for slot provider module {module_name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    previous_dont_write_bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous_dont_write_bytecode
    return module


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
        "package_digest": dict(signature.package_digest)
        if signature.package_digest is not None
        else None,
        "signature_path": str(signature.signature_path) if signature.signature_path else "",
        "reason": signature.reason,
        "revocation_checked": signature.revocation_checked,
    }

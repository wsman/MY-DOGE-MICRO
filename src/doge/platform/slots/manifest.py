"""Slot manifest contract (v1).

A :class:`SlotManifest` is the declarative contract for a platform contribution.
This module defines the in-memory dataclass model and a strict loader
(:func:`load_slot_manifest`) that accepts Python dicts or JSON files and rejects
unknown top-level keys so schema evolution must go through ``schema_version``.

YAML-on-disk parsing is intentionally deferred (a separate dependency ADR is
required before third-party slot installation). Sprint 033 supports dict and JSON
inputs only; built-in slots construct :class:`SlotManifest` directly in Python.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Union

from doge.platform.slots.errors import SlotManifestValidationError

SCHEMA_VERSION = 1
_MAX_ID_LEN = 64

_ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:[.-][a-z][a-z0-9]*)*$")
_ENTRYPOINT_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_.]*$")
_NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

_VALID_MATURITY = ("experimental", "alpha", "beta", "stable")
_VALID_RISK = ("low", "medium", "high", "forbidden")
_VALID_HEALTH_STATUS = ("experimental", "healthy", "degraded", "disabled")
_VALID_ACCESS = ("none", "read", "write")
_VALID_TOGGLE = ("none", "allow")

# Top-level keys permitted in a v1 manifest dict. Unknown keys are rejected so
# schema changes are forced through ``schema_version``.
_ALLOWED_TOP_KEYS = frozenset(
    {
        "schema_version",
        "id",
        "name",
        "version",
        "type",
        "owner",
        "maturity",
        "description",
        "entrypoint",
        "provides",
        "requires",
        "permissions",
        "health",
        "feature_flags",
        "compatibility",
    }
)


class SlotType(str, Enum):
    """Slot contribution type.

    ``tool`` is exercised in Sprint 033; ``model`` has one backend proof in
    Sprint 034. Other types remain representability-only until later sprints.
    """

    TOOL = "tool"
    MODEL = "model"
    WORKFLOW = "workflow"
    DATA = "data"
    DOCUMENT = "document"
    UI = "ui"
    GATEWAY = "gateway"
    GOVERNANCE = "governance"
    EVAL = "eval"
    WATCHER = "watcher"


@dataclass(frozen=True)
class SlotProvides:
    """What a slot contributes. At least one of tools/capabilities is required."""

    tools: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SlotRequirement:
    """A dependency on another slot, service, or feature flag."""

    kind: str
    id: str
    optional: bool = False


@dataclass(frozen=True)
class SlotPermissions:
    """Declarative permission surface (NOT enforced in Sprint 033)."""

    filesystem: str = "none"
    network: str = "none"
    shell: str = "none"
    database: str = "none"
    secrets: tuple[str, ...] = ()
    risk_level: str = "low"


@dataclass(frozen=True)
class SlotHealth:
    """Static health descriptor (no active probes in Sprint 033)."""

    status: str = "experimental"
    notes: str = ""


@dataclass(frozen=True)
class SlotCompatibility:
    """Compatibility and supersession metadata."""

    runtime_min: str = "1"
    replaces: tuple[str, ...] = ()
    breaking: bool = False


@dataclass(frozen=True)
class SlotManifest:
    """Canonical v1 slot manifest (single source of truth for a contribution)."""

    schema_version: int
    id: str
    name: str
    version: str
    type: SlotType
    owner: str
    maturity: str
    description: str
    entrypoint: str
    provides: SlotProvides
    requires: tuple[SlotRequirement, ...] = ()
    permissions: SlotPermissions = field(default_factory=SlotPermissions)
    health: SlotHealth = field(default_factory=SlotHealth)
    feature_flags: tuple[str, ...] = ()
    compatibility: SlotCompatibility = field(default_factory=SlotCompatibility)


ManifestSource = Union[Mapping[str, Any], str, Path]


def load_slot_manifest(source: ManifestSource) -> SlotManifest:
    """Load and validate a :class:`SlotManifest` from a dict or JSON file path.

    Raises :class:`SlotManifestValidationError` on any schema violation,
    including unknown top-level keys.
    """
    data = _coerce_to_dict(source)
    _reject_unknown_top_keys(data)

    schema_version = _require(data, "schema_version")
    if schema_version != SCHEMA_VERSION:
        raise SlotManifestValidationError(
            f"schema_version must be {SCHEMA_VERSION}; got {schema_version!r}"
        )

    slot_id = _require(data, "id")
    _validate_id(slot_id)

    name = _require(data, "name")
    if not isinstance(name, str) or not 1 <= len(name) <= 120:
        raise SlotManifestValidationError("name must be a string of 1..120 chars")

    version = _require(data, "version")
    if not isinstance(version, str) or not version.strip():
        raise SlotManifestValidationError("version must be a non-empty string")

    slot_type = _validate_type(_require(data, "type"))

    owner = _require(data, "owner")
    if not isinstance(owner, str) or not owner.strip():
        raise SlotManifestValidationError(
            "owner must be a non-empty bounded-context slug"
        )

    maturity = _require(data, "maturity")
    if maturity not in _VALID_MATURITY:
        raise SlotManifestValidationError(
            f"maturity must be one of {_VALID_MATURITY}; got {maturity!r}"
        )

    description = _require(data, "description")
    if not isinstance(description, str) or not 1 <= len(description) <= 2000:
        raise SlotManifestValidationError(
            "description must be a string of 1..2000 chars"
        )

    entrypoint = _require(data, "entrypoint")
    if not isinstance(entrypoint, str) or not _ENTRYPOINT_RE.match(entrypoint):
        raise SlotManifestValidationError(
            "entrypoint must be a dotted python path (e.g. pkg.mod:Class)"
        )

    provides = _build_provides(_require(data, "provides"))
    requires = _build_requires(data.get("requires", []))
    permissions = _build_permissions(data.get("permissions", {}))
    health = _build_health(data.get("health", {}))
    feature_flags = _build_feature_flags(data.get("feature_flags", []))
    compatibility = _build_compatibility(data.get("compatibility", {}))

    return SlotManifest(
        schema_version=schema_version,
        id=slot_id,
        name=name,
        version=version,
        type=slot_type,
        owner=owner,
        maturity=maturity,
        description=description,
        entrypoint=entrypoint,
        provides=provides,
        requires=requires,
        permissions=permissions,
        health=health,
        feature_flags=feature_flags,
        compatibility=compatibility,
    )


def _coerce_to_dict(source: ManifestSource) -> dict[str, Any]:
    if isinstance(source, Mapping):
        return dict(source)
    if isinstance(source, (str, Path)):
        path = Path(source)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise SlotManifestValidationError(
                f"cannot read manifest file {source}: {exc}"
            ) from exc
        try:
            loaded = json.loads(text)
        except json.JSONDecodeError as exc:
            raise SlotManifestValidationError(
                f"manifest file {source} is not valid JSON: {exc}"
            ) from exc
        if not isinstance(loaded, dict):
            raise SlotManifestValidationError(
                f"manifest file {source} must contain a JSON object"
            )
        return loaded
    raise SlotManifestValidationError(
        f"manifest source must be a dict or path; got {type(source).__name__}"
    )


def _reject_unknown_top_keys(data: Mapping[str, Any]) -> None:
    unknown = set(data) - _ALLOWED_TOP_KEYS
    if unknown:
        raise SlotManifestValidationError(
            f"unknown manifest keys {sorted(unknown)}; allowed {sorted(_ALLOWED_TOP_KEYS)}"
        )


def _require(data: Mapping[str, Any], key: str) -> Any:
    if key not in data:
        raise SlotManifestValidationError(f"missing required field: {key}")
    return data[key]


def _validate_id(slot_id: Any) -> None:
    if (
        not isinstance(slot_id, str)
        or len(slot_id) > _MAX_ID_LEN
        or not _ID_RE.match(slot_id)
    ):
        raise SlotManifestValidationError(
            f"id must match {_ID_RE.pattern} (max {_MAX_ID_LEN} chars); got {slot_id!r}"
        )


def _validate_type(type_value: Any) -> SlotType:
    try:
        return SlotType(type_value)
    except ValueError as exc:
        raise SlotManifestValidationError(
            f"type must be one of {[t.value for t in SlotType]}; got {type_value!r}"
        ) from exc


def _validate_name_list(value: Any, label: str, regex: re.Pattern[str]) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise SlotManifestValidationError(f"{label} must be a list of strings")
    out: list[str] = []
    for item in value:
        if not isinstance(item, str) or not regex.match(item):
            raise SlotManifestValidationError(
                f"{label} entry {item!r} must match {regex.pattern}"
            )
        out.append(item)
    return tuple(out)


def _build_provides(provides_data: Any) -> SlotProvides:
    if not isinstance(provides_data, Mapping):
        raise SlotManifestValidationError("provides must be a mapping")
    tools = _validate_name_list(provides_data.get("tools", []), "provides.tools", _NAME_RE)
    capabilities = _validate_name_list(
        provides_data.get("capabilities", []), "provides.capabilities", _NAME_RE
    )
    if not tools and not capabilities:
        raise SlotManifestValidationError(
            "provides must declare at least one tool or capability"
        )
    metadata = provides_data.get("metadata", {})
    if not isinstance(metadata, Mapping):
        raise SlotManifestValidationError("provides.metadata must be a mapping")
    return SlotProvides(tools=tools, capabilities=capabilities, metadata=dict(metadata))


def _build_requires(requires_data: Any) -> tuple[SlotRequirement, ...]:
    if not isinstance(requires_data, (list, tuple)):
        raise SlotManifestValidationError("requires must be a list")
    out: list[SlotRequirement] = []
    for item in requires_data:
        if not isinstance(item, Mapping):
            raise SlotManifestValidationError("each requires entry must be a mapping")
        kind = item.get("kind")
        rid = item.get("id")
        if not isinstance(kind, str) or not kind.strip():
            raise SlotManifestValidationError(
                "requires[].kind must be a non-empty string"
            )
        if not isinstance(rid, str) or not rid.strip():
            raise SlotManifestValidationError(
                "requires[].id must be a non-empty string"
            )
        out.append(
            SlotRequirement(kind=kind, id=rid, optional=bool(item.get("optional", False)))
        )
    return tuple(out)


def _enum(label: str, value: Any, valid: tuple[str, ...]) -> str:
    if value not in valid:
        raise SlotManifestValidationError(
            f"{label} must be one of {valid}; got {value!r}"
        )
    return value


def _build_permissions(perm_data: Any) -> SlotPermissions:
    if not isinstance(perm_data, Mapping):
        raise SlotManifestValidationError("permissions must be a mapping")
    secrets = perm_data.get("secrets", [])
    if not isinstance(secrets, (list, tuple)):
        raise SlotManifestValidationError("permissions.secrets must be a list")
    return SlotPermissions(
        filesystem=_enum("permissions.filesystem", perm_data.get("filesystem", "none"), _VALID_ACCESS),
        network=_enum("permissions.network", perm_data.get("network", "none"), _VALID_TOGGLE),
        shell=_enum("permissions.shell", perm_data.get("shell", "none"), _VALID_TOGGLE),
        database=_enum("permissions.database", perm_data.get("database", "none"), _VALID_ACCESS),
        risk_level=_enum("permissions.risk_level", perm_data.get("risk_level", "low"), _VALID_RISK),
        secrets=tuple(secrets),
    )


def _build_health(health_data: Any) -> SlotHealth:
    if health_data is None or health_data == {}:
        return SlotHealth()
    if isinstance(health_data, str):
        status, notes = health_data, ""
    elif isinstance(health_data, Mapping):
        status = health_data.get("status", "experimental")
        notes = health_data.get("notes", "")
    else:
        raise SlotManifestValidationError("health must be a mapping or status string")
    if status not in _VALID_HEALTH_STATUS:
        raise SlotManifestValidationError(
            f"health.status must be one of {_VALID_HEALTH_STATUS}; got {status!r}"
        )
    if not isinstance(notes, str):
        raise SlotManifestValidationError("health.notes must be a string")
    return SlotHealth(status=status, notes=notes)


def _build_feature_flags(ff_data: Any) -> tuple[str, ...]:
    if not isinstance(ff_data, (list, tuple)):
        raise SlotManifestValidationError(
            "feature_flags must be a list of Settings feature-field keys"
        )
    out: list[str] = []
    for item in ff_data:
        if not isinstance(item, str) or not item.strip():
            raise SlotManifestValidationError(
                "feature_flags entries must be non-empty Settings field keys"
            )
        out.append(item)
    return tuple(out)


def _build_compatibility(comp_data: Any) -> SlotCompatibility:
    if not isinstance(comp_data, Mapping):
        raise SlotManifestValidationError("compatibility must be a mapping")
    runtime_min = comp_data.get("runtime_min", "1")
    if not isinstance(runtime_min, str) or not runtime_min.strip():
        raise SlotManifestValidationError(
            "compatibility.runtime_min must be a non-empty string"
        )
    replaces = comp_data.get("replaces", [])
    if not isinstance(replaces, (list, tuple)):
        raise SlotManifestValidationError("compatibility.replaces must be a list")
    breaking = comp_data.get("breaking", False)
    if not isinstance(breaking, bool):
        raise SlotManifestValidationError("compatibility.breaking must be a bool")
    return SlotCompatibility(
        runtime_min=runtime_min, replaces=tuple(replaces), breaking=breaking
    )

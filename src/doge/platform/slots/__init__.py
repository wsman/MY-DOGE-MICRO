"""Slot Platform Foundation (ADR-0042).

Public contract for modular platform contributions. A *slot* declares what it
provides (tools, capabilities, ...), what it requires, its permissions, health,
feature flags, and compatibility. The :class:`SlotRegistry` aggregates slot
contributions for runtime assembly.

Sprint 033 ships only the ``tool`` slot type (``market.core``); the contract
declares the full :class:`SlotType` enum so future sprints migrate model,
workflow, data, document, ui, gateway, governance, eval, and watcher slots
without changing the manifest schema.

This package is deliberately pure: it imports only ``doge.core.*``,
``doge.shared.*`` and the standard library. It must not import ``doge.config``,
``doge.infrastructure``, ``doge.adapters``, ``doge.products``,
``doge.application.tools``, ``doge.bootstrap`` or ``doge.interfaces``;
``tests/unit/architecture/test_slot_boundary.py`` ratchets this.
"""

from __future__ import annotations

from doge.platform.slots.contracts import (
    ISlot,
    SlotContribution,
    SlotContext,
    SlotStatus,
    ToolServiceProtocol,
)
from doge.platform.slots.errors import (
    SlotAlreadyRegisteredError,
    SlotConfigurationError,
    SlotError,
    SlotManifestValidationError,
    UnknownSlotError,
)
from doge.platform.slots.manifest import (
    SCHEMA_VERSION,
    SlotCompatibility,
    SlotHealth,
    SlotManifest,
    SlotPermissions,
    SlotProvides,
    SlotRequirement,
    SlotType,
    load_slot_manifest,
)
from doge.platform.slots.registry import SlotRegistry, SlotStatusRecord

__all__ = [
    "ISlot",
    "SCHEMA_VERSION",
    "SlotAlreadyRegisteredError",
    "SlotCompatibility",
    "SlotConfigurationError",
    "SlotContribution",
    "SlotContext",
    "SlotError",
    "SlotHealth",
    "SlotManifest",
    "SlotManifestValidationError",
    "SlotPermissions",
    "SlotProvides",
    "SlotRegistry",
    "SlotRequirement",
    "SlotStatus",
    "SlotStatusRecord",
    "SlotType",
    "ToolServiceProtocol",
    "UnknownSlotError",
    "load_slot_manifest",
]

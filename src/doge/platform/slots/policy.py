"""Slot enablement policy.

Policies are pure, in-memory rules over already-registered slot manifests. They
do not read environment variables or settings directly; callers pass a
``SlotContext`` whose feature flags were resolved by the bootstrap layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from doge.platform.slots.contracts import SlotContext
from doge.platform.slots.errors import SlotConfigurationError
from doge.platform.slots.manifest import SlotManifest

if TYPE_CHECKING:
    from doge.platform.slots.bundles import SlotBundle


@dataclass(frozen=True)
class SlotPolicy:
    """Enable/disable rules applied after registry membership and before resolve."""

    enabled_slots: tuple[str, ...] = ()
    disabled_slots: tuple[str, ...] = ()
    installed_slots: tuple[str, ...] = ()
    enforce_feature_flags: bool = True

    def __post_init__(self) -> None:
        overlap = set(self.enabled_slots) & set(self.disabled_slots)
        if overlap:
            raise SlotConfigurationError(
                "slot policy cannot both enable and disable slot(s): "
                + ", ".join(sorted(overlap))
            )

    @classmethod
    def from_bundle(
        cls,
        bundle: "SlotBundle",
        *,
        installed_slots: tuple[str, ...] = (),
    ) -> "SlotPolicy":
        """Build a policy that admits only a bundle's slots."""

        return cls(
            enabled_slots=bundle.slot_ids,
            disabled_slots=bundle.disabled_slot_ids,
            installed_slots=installed_slots,
        )

    def allows(self, manifest: SlotManifest, context: SlotContext) -> bool:
        """Return whether ``manifest`` is enabled by this policy and context."""

        if manifest.id in self.disabled_slots:
            return False
        if (
            self.enabled_slots
            and manifest.id not in self.enabled_slots
            and manifest.id not in self.installed_slots
        ):
            return False
        if not self.enforce_feature_flags:
            return True
        return all(context.feature_flags.get(flag, False) for flag in manifest.feature_flags)

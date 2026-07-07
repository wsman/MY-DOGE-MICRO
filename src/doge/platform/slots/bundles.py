"""Read-only slot bundle contracts."""

from __future__ import annotations

from dataclasses import dataclass

from doge.platform.slots.errors import SlotConfigurationError


@dataclass(frozen=True)
class SlotBundle:
    """A named set of slots for a user/operator scenario."""

    id: str
    name: str
    description: str
    slot_ids: tuple[str, ...]
    disabled_slot_ids: tuple[str, ...] = ()
    maturity: str = "experimental"
    def __post_init__(self) -> None:
        if not self.id.startswith("bundle."):
            raise SlotConfigurationError(f"slot bundle id must start with bundle.: {self.id}")
        if not self.slot_ids:
            raise SlotConfigurationError(f"slot bundle {self.id} must include at least one slot")
        overlap = set(self.slot_ids) & set(self.disabled_slot_ids)
        if overlap:
            raise SlotConfigurationError(
                f"slot bundle {self.id} cannot include disabled slot(s): "
                + ", ".join(sorted(overlap))
            )


@dataclass(frozen=True)
class SlotBundleStatus:
    """Read-only status row for bundle discovery surfaces."""

    id: str
    name: str
    description: str
    status: str
    slot_ids: tuple[str, ...]
    enabled_slot_ids: tuple[str, ...]
    disabled_slot_ids: tuple[str, ...]
    missing_slot_ids: tuple[str, ...] = ()
    maturity: str = "experimental"

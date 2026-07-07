"""Disk manifest loader for local Slot Platform previews."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from doge.platform.slots.contracts import ISlot, SlotContribution, SlotContext
from doge.platform.slots.errors import SlotConfigurationError
from doge.platform.slots.manifest import SlotManifest, load_slot_manifest


@dataclass(frozen=True)
class ManifestOnlySlot(ISlot):
    """Slot backed only by a validated manifest.

    Sprint 046 loads disk manifests for discovery and policy diagnostics only.
    It does not import provider code or execute third-party entrypoints.
    """

    slot_manifest: SlotManifest
    source_path: Path

    def manifest(self) -> SlotManifest:
        return self.slot_manifest

    def resolve(self, context: SlotContext) -> SlotContribution:
        return SlotContribution(slot_id=self.slot_manifest.id)


class SlotLoader:
    """Load manifest-only slots from JSON files or manifest directories."""

    def load(self, sources: Iterable[str | Path]) -> tuple[ManifestOnlySlot, ...]:
        slots: list[ManifestOnlySlot] = []
        for path in _discover_manifest_paths(sources):
            try:
                manifest = load_slot_manifest(path)
            except Exception as exc:  # noqa: BLE001 - annotate manifest path
                raise SlotConfigurationError(f"failed to load slot manifest {path}: {exc}") from exc
            slots.append(ManifestOnlySlot(manifest, path))
        return tuple(slots)


def _discover_manifest_paths(sources: Iterable[str | Path]) -> tuple[Path, ...]:
    paths: list[Path] = []
    for source in sources:
        root = Path(source)
        if root.is_file():
            paths.append(root)
            continue
        if not root.exists():
            raise SlotConfigurationError(f"slot manifest source does not exist: {root}")
        if not root.is_dir():
            raise SlotConfigurationError(f"slot manifest source is not a file or directory: {root}")
        paths.extend(sorted(root.glob("*.json")))
        paths.extend(sorted(root.glob("*/slot.json")))
    return tuple(_dedupe(paths))


def _dedupe(paths: Iterable[Path]) -> tuple[Path, ...]:
    seen: set[Path] = set()
    out: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        out.append(path)
    return tuple(out)

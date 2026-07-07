"""Slot-backed UI panel registry for workspace surfaces."""

from __future__ import annotations

from dataclasses import asdict
from typing import Iterable

from doge.platform.slots import SlotConfigurationError, UIPanelContribution


class UIPanelRegistry:
    """Read-only registry over slot-contributed frontend panel metadata."""

    def __init__(self, panels: Iterable[UIPanelContribution]) -> None:
        self._panels = tuple(panels)
        seen: set[tuple[str, str]] = set()
        for panel in self._panels:
            key = (panel.workspace, panel.panel_id)
            if key in seen:
                raise SlotConfigurationError(
                    f"duplicate UI panel contribution: {panel.workspace}.{panel.panel_id}"
                )
            seen.add(key)

    def panels_for(
        self,
        workspace: str,
        *,
        zone: str | None = None,
        mode: str | None = None,
    ) -> tuple[UIPanelContribution, ...]:
        """Return panels for a workspace, ordered by contribution order."""

        panels = [
            panel
            for panel in self._panels
            if panel.workspace == workspace
            and (zone is None or panel.zone == zone)
            and (mode is None or not panel.modes or mode in panel.modes)
        ]
        return tuple(sorted(panels, key=lambda panel: (panel.order, panel.panel_id)))

    def rows(
        self,
        *,
        workspace: str | None = None,
        zone: str | None = None,
        mode: str | None = None,
    ) -> tuple[dict[str, object], ...]:
        """Serialize panel metadata for API and Web consumers."""

        panels = (
            self.panels_for(workspace, zone=zone, mode=mode)
            if workspace is not None
            else tuple(sorted(self._panels, key=lambda panel: (panel.workspace, panel.order, panel.panel_id)))
        )
        rows: list[dict[str, object]] = []
        for panel in panels:
            if zone is not None and panel.zone != zone:
                continue
            if mode is not None and panel.modes and mode not in panel.modes:
                continue
            row = asdict(panel)
            row["modes"] = list(panel.modes)
            row["required_artifact_fields"] = list(panel.required_artifact_fields)
            rows.append(row)
        return tuple(rows)

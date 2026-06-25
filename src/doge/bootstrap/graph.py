"""Process object graph for bootstrap-owned containers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ProcessGraph:
    """Long-lived object graph for one process role.

    Compatibility containers remain the public factory surface, but they all
    point at one graph so sibling containers do not construct each other.
    """

    db_path: Path | str | None
    role: str
    runtime_container: Any
    gateway_container: Any
    workspace_container: Any

    def as_app_container(self):
        """Return an AppContainer view over this process graph."""

        from doge.bootstrap.container import AppContainer

        return AppContainer(
            runtime=self.runtime_container,
            workspace=self.workspace_container,
            gateway=self.gateway_container,
        )

    @property
    def app_container(self):
        """Compatibility alias for callers that expect an app container."""

        return self.as_app_container()

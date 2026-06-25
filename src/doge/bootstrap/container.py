"""Top-level application bootstrap container."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from doge.bootstrap.gateway import GatewayContainer
from doge.bootstrap.runtime import RuntimeContainer
from doge.bootstrap.workspace import WorkspaceContainer


@dataclass(frozen=True)
class AppContainer:
    """Typed aggregate for bounded-context bootstrap containers."""

    runtime: RuntimeContainer
    workspace: WorkspaceContainer
    gateway: GatewayContainer


def build_app_container(db_path: Path | str | None = None) -> AppContainer:
    """Build the aggregate application container."""

    from doge.bootstrap.processes import build_embedded_process

    return build_embedded_process(db_path=db_path).app_container

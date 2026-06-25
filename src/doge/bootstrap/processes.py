"""Process-root factories for bootstrap composition."""

from __future__ import annotations

from pathlib import Path

from doge.bootstrap.container import AppContainer
from doge.bootstrap.gateway import GatewayContainer
from doge.bootstrap.graph import ProcessGraph
from doge.bootstrap.runtime import RuntimeContainer
from doge.bootstrap.workspace import WorkspaceContainer


def build_embedded_process(db_path: Path | str | None = None) -> ProcessGraph:
    """Build the embedded CLI/process graph."""

    return _build_process_graph(db_path=db_path, role="embedded")


def build_api_process(db_path: Path | str | None = None) -> ProcessGraph:
    """Build the daemon/API process graph."""

    return _build_process_graph(db_path=db_path, role="api")


def build_worker_process(db_path: Path | str | None = None) -> ProcessGraph:
    """Build the background worker process graph."""

    return _build_process_graph(db_path=db_path, role="worker")


def _build_process_graph(*, db_path: Path | str | None, role: str) -> ProcessGraph:
    graph_box: dict[str, ProcessGraph] = {}

    def get_graph() -> ProcessGraph:
        return graph_box["graph"]

    runtime = RuntimeContainer(db_path=db_path, graph_provider=get_graph)
    workspace = WorkspaceContainer(db_path=db_path, graph_provider=get_graph)
    gateway = GatewayContainer(db_path=db_path, graph_provider=get_graph)
    graph = ProcessGraph(
        db_path=db_path,
        role=role,
        runtime_container=runtime,
        gateway_container=gateway,
        workspace_container=workspace,
    )
    graph_box["graph"] = graph
    return graph

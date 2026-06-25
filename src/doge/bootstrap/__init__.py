"""Bootstrap containers for bounded-context wiring."""

from doge.bootstrap.container import AppContainer, build_app_container
from doge.bootstrap.gateway import GatewayContainer, build_gateway_container
from doge.bootstrap.graph import ProcessGraph
from doge.bootstrap.processes import build_api_process, build_embedded_process, build_worker_process
from doge.bootstrap.runtime import RuntimeContainer, build_runtime_container
from doge.bootstrap.workspace import WorkspaceContainer, build_workspace_container

__all__ = [
    "AppContainer",
    "GatewayContainer",
    "ProcessGraph",
    "RuntimeContainer",
    "WorkspaceContainer",
    "build_app_container",
    "build_api_process",
    "build_embedded_process",
    "build_gateway_container",
    "build_runtime_container",
    "build_worker_process",
    "build_workspace_container",
]

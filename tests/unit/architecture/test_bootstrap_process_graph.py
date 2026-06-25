"""Architecture tests for process-owned bootstrap graphs."""

from __future__ import annotations

import pytest

from doge.bootstrap import (
    GatewayContainer,
    ProcessGraph,
    RuntimeContainer,
    WorkspaceContainer,
    build_api_process,
    build_embedded_process,
    build_worker_process,
)


@pytest.mark.parametrize(
    ("builder", "role"),
    [
        (build_embedded_process, "embedded"),
        (build_api_process, "api"),
        (build_worker_process, "worker"),
    ],
)
def test_process_builders_return_graph_owned_containers(builder, role, tmp_path) -> None:
    graph = builder(tmp_path / f"{role}.db")

    assert isinstance(graph, ProcessGraph)
    assert graph.role == role
    assert isinstance(graph.runtime_container, RuntimeContainer)
    assert isinstance(graph.gateway_container, GatewayContainer)
    assert isinstance(graph.workspace_container, WorkspaceContainer)

    assert graph.runtime_container.gateway_container() is graph.gateway_container
    assert graph.gateway_container.runtime_container() is graph.runtime_container
    assert graph.gateway_container.workspace_container() is graph.workspace_container
    assert graph.workspace_container.runtime_container() is graph.runtime_container


def test_app_container_view_preserves_process_container_identity(tmp_path) -> None:
    graph = build_api_process(tmp_path / "api.db")
    app_container = graph.as_app_container()

    assert app_container.runtime is graph.runtime_container
    assert app_container.gateway is graph.gateway_container
    assert app_container.workspace is graph.workspace_container

"""Gateway router aggregation parity checks."""

from __future__ import annotations

import importlib

from fastapi.routing import APIRoute


def _routes(router) -> set[tuple[str, str]]:
    routes: set[tuple[str, str]] = set()
    for route in router.routes:
        if isinstance(route, APIRoute):
            for method in route.methods:
                if method in {"GET", "POST", "PUT", "DELETE", "PATCH"}:
                    routes.add((method, route.path))
    return routes


def test_runs_router_aggregates_query_action_and_stream_subrouters() -> None:
    from doge.interfaces.gateway.routers import run_actions, run_queries, run_stream, runs

    child_routes = _routes(run_queries.router) | _routes(run_actions.router) | _routes(run_stream.router)

    assert _routes(runs.router) == child_routes
    assert ("POST", "/runs/{run_id}/resume") in child_routes


def test_legacy_v1_router_shims_export_canonical_gateway_routers() -> None:
    module_names = [
        "audit",
        "capabilities",
        "case_runs",
        "cases",
        "documents",
        "enterprise",
        "health",
        "platform",
        "portfolios",
        "projects",
        "run_actions",
        "run_queries",
        "run_stream",
        "runs",
        "sessions",
        "tools",
        "workflows",
        "workspaces",
    ]

    for name in module_names:
        legacy = importlib.import_module(f"doge.interfaces.api.routers.v1.{name}")
        canonical = importlib.import_module(f"doge.interfaces.gateway.routers.{name}")
        assert legacy.router is canonical.router

"""Gateway router aggregation parity checks."""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

from fastapi.routing import APIRoute


PROJECT_ROOT = Path(__file__).resolve().parents[3]
V1_SHIM_ROOT = PROJECT_ROOT / "src" / "doge" / "interfaces" / "api" / "routers" / "v1"
GATEWAY_ROOT = PROJECT_ROOT / "src" / "doge" / "interfaces" / "gateway" / "routers"


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
    for name in _shim_module_names():
        legacy = importlib.import_module(f"doge.interfaces.api.routers.v1.{name}")
        canonical = importlib.import_module(f"doge.interfaces.gateway.routers.{name}")
        if hasattr(canonical, "router"):
            assert legacy.router is canonical.router


def test_v1_shim_file_set_matches_gateway_router_file_set() -> None:
    assert _python_filenames(V1_SHIM_ROOT) == _python_filenames(GATEWAY_ROOT)


def test_v1_router_shims_contain_no_behavior_logic() -> None:
    for path in sorted(V1_SHIM_ROOT.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        body = _without_module_docstring(tree.body)
        if path.name == "__init__.py":
            assert body == [], f"{path} must only document the compatibility package"
            continue
        if path.name == "run_stream.py":
            assert _is_run_stream_compat_export(body), f"{path} has unexpected compatibility logic"
            continue
        assert len(body) == 1, f"{path} must only re-export its gateway module"
        node = body[0]
        assert isinstance(node, ast.ImportFrom), f"{path} contains behavior instead of a re-export"
        assert node.module == f"doge.interfaces.gateway.routers.{path.stem}"
        assert len(node.names) == 1
        assert node.names[0].name == "*"


def test_v1_shim_public_exports_match_canonical_gateway_modules() -> None:
    for name in _shim_module_names():
        legacy = importlib.import_module(f"doge.interfaces.api.routers.v1.{name}")
        canonical = importlib.import_module(f"doge.interfaces.gateway.routers.{name}")
        legacy_public = {item for item in dir(legacy) if not item.startswith("_")}
        if hasattr(canonical, "router"):
            assert legacy.router is canonical.router
        canonical_all = getattr(canonical, "__all__", None)
        if canonical_all is not None:
            assert set(canonical_all) <= legacy_public


def _python_filenames(root: Path) -> set[str]:
    return {path.name for path in root.glob("*.py")}


def _shim_module_names() -> list[str]:
    return [
        path.stem
        for path in sorted(V1_SHIM_ROOT.glob("*.py"))
        if path.name != "__init__.py"
    ]


def _without_module_docstring(nodes: list[ast.stmt]) -> list[ast.stmt]:
    if nodes and isinstance(nodes[0], ast.Expr) and isinstance(nodes[0].value, ast.Constant):
        if isinstance(nodes[0].value.value, str):
            return nodes[1:]
    return nodes


def _is_run_stream_compat_export(nodes: list[ast.stmt]) -> bool:
    if len(nodes) != 3:
        return False
    first, second, third = nodes
    return (
        isinstance(first, ast.ImportFrom)
        and first.module == "doge.interfaces.api.handlers"
        and [alias.name for alias in first.names] == ["RunStreamHandler"]
        and isinstance(second, ast.ImportFrom)
        and second.module == "doge.interfaces.gateway.routers.run_stream"
        and len(second.names) == 1
        and second.names[0].name == "*"
        and isinstance(third, ast.Assign)
    )

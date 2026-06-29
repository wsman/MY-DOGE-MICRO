from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]

_LEGACY_ROUTER_PREFIXES = {
    "src/doge/interfaces/api_legacy/routers/agent.py": "/api/agent",
    "src/doge/interfaces/api_legacy/routers/analysis.py": "/api/analysis",
    "src/doge/interfaces/api_legacy/routers/config.py": "/api/config",
    "src/doge/interfaces/api_legacy/routers/data.py": "/api/data",
    "src/doge/interfaces/api_legacy/routers/documents.py": "/api/documents",
    "src/doge/interfaces/api_legacy/routers/macro.py": "/api/macro",
    "src/doge/interfaces/api_legacy/routers/notes.py": "/api/notes",
    "src/doge/interfaces/api_legacy/routers/scan.py": "/api/scan",
}

_EXPECTED_LEGACY_ROUTES = {
    "DELETE /api/notes/{note_id}",
    "GET /api/agent/runs/{run_id}",
    "GET /api/agent/runs/{run_id}/approvals",
    "GET /api/agent/runs/{run_id}/artifacts",
    "GET /api/agent/runs/{run_id}/events",
    "GET /api/agent/runs/{run_id}/stream",
    "GET /api/analysis/reports",
    "GET /api/analysis/reports/{report_id}",
    "GET /api/config",
    "GET /api/config/settings",
    "GET /api/data/{market}/table/{table_name}",
    "GET /api/data/{market}/tables",
    "GET /api/data/{market}/ticker-names",
    "GET /api/data/{market}/ticker/{ticker}/kline",
    "GET /api/health",
    "GET /api/macro/reports",
    "GET /api/macro/reports/latest",
    "GET /api/macro/reports/{report_id}",
    "GET /api/notes/recent",
    "GET /api/notes/search",
    "GET /api/notes/ticker/{ticker}",
    "GET /api/notes/tracked",
    "GET /api/scan/servers",
    "GET /api/scan/status",
    "GET /api/stats",
    "POST /api/agent/runs",
    "POST /api/agent/runs/{run_id}/approvals/{approval_id}",
    "POST /api/documents",
    "POST /api/macro/run",
    "POST /api/notes",
    "POST /api/scan/{market}",
    "POST /api/scan/servers/test",
    "POST /api/config/validate-tdx",
    "PUT /api/config/settings",
}


def test_no_new_legacy_api_function_routes() -> None:
    routes = set()
    for relative, prefix in _LEGACY_ROUTER_PREFIXES.items():
        routes.update(_decorated_routes(ROOT / relative, prefix))

    main = (ROOT / "src/doge/interfaces/api/main.py").read_text(encoding="utf-8")
    assert '@app.get("/api/health")' in main
    assert 'target_app.add_api_route("/api/stats", stats, methods=["GET"])' in main
    routes.add("GET /api/health")
    routes.add("GET /api/stats")

    assert routes == _EXPECTED_LEGACY_ROUTES


def _decorated_routes(path: Path, prefix: str) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    routes: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            continue
        for decorator in node.decorator_list:
            route = _route_from_decorator(decorator, prefix)
            if route is not None:
                routes.add(route)
    return routes


def _route_from_decorator(node: ast.AST, prefix: str) -> str | None:
    if not isinstance(node, ast.Call):
        return None
    if not isinstance(node.func, ast.Attribute):
        return None
    method = node.func.attr.upper()
    if method not in {"GET", "POST", "PUT", "DELETE", "PATCH"}:
        return None
    if not node.args or not isinstance(node.args[0], ast.Constant):
        return None
    suffix = node.args[0].value
    if not isinstance(suffix, str):
        return None
    return f"{method} {prefix}{suffix}"

"""AST guards for behavior-free compatibility shims."""

from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SHIM_FILES = [
    PROJECT_ROOT / "src" / "doge" / "application" / "agent" / "tools.py",
    PROJECT_ROOT / "src" / "doge" / "interfaces" / "api" / "routers" / "__init__.py",
]

SQL_MARKERS = (
    "SELECT ",
    "INSERT ",
    "UPDATE ",
    "DELETE ",
    "CREATE TABLE",
    "DROP TABLE",
    "PRAGMA ",
)
HTTP_METHODS = {"get", "post", "put", "delete", "patch", "head", "options"}
TOOL_REGISTRATION_METHODS = {"register", "register_tool", "add_tool"}


def test_shim_files_must_not_import_infrastructure_adapters() -> None:
    for path, tree in _shim_trees():
        illegal = [
            name
            for name in _import_targets(tree)
            if name == "doge.infrastructure" or name.startswith("doge.infrastructure.")
        ]

        assert illegal == [], f"{_display(path)} imports infrastructure adapters: {illegal}"


def test_shim_files_must_not_contain_sql_strings() -> None:
    for path, tree in _shim_trees():
        body = _without_module_docstring(tree.body)
        illegal = []
        for node in ast.walk(ast.Module(body=body, type_ignores=[])):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                upper = node.value.upper()
                if any(marker in upper for marker in SQL_MARKERS):
                    illegal.append(node.value)

        assert illegal == [], f"{_display(path)} contains SQL-looking strings: {illegal}"


def test_shim_files_must_not_open_sqlite_duckdb_connections() -> None:
    for path, tree in _shim_trees():
        illegal = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr in {"connect", "cursor", "execute"}:
                illegal.append(func.attr)
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                if func.value.id in {"sqlite3", "duckdb"} and func.attr == "connect":
                    illegal.append(f"{func.value.id}.connect")

        assert illegal == [], f"{_display(path)} opens or uses DB connections: {illegal}"


def test_shim_files_must_not_define_api_router_behavior() -> None:
    for path, tree in _shim_trees():
        illegal = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                if _call_name(node.value.func) == "APIRouter":
                    illegal.append("router = APIRouter(...)")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in HTTP_METHODS and _is_router_like(node.func.value):
                    illegal.append(f"router.{node.func.attr}(...)")

        assert illegal == [], f"{_display(path)} defines API router behavior: {illegal}"


def test_shim_files_must_not_instantiate_runtime_kernel() -> None:
    for path, tree in _shim_trees():
        calls = [
            _call_name(node.func)
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and _call_name(node.func) == "RuntimeKernel"
        ]

        assert calls == [], f"{_display(path)} instantiates RuntimeKernel"


def test_shim_files_must_not_register_tools() -> None:
    for path, tree in _shim_trees():
        illegal = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in TOOL_REGISTRATION_METHODS:
                    illegal.append(node.func.attr)

        assert illegal == [], f"{_display(path)} registers tools: {illegal}"


def test_shim_files_must_not_implement_approval_policy() -> None:
    _assert_no_named_behavior(("approval", "policy", "authorize", "permit"))


def test_shim_files_must_not_implement_worker_behavior() -> None:
    _assert_no_named_behavior(("worker", "poll", "dequeue", "process_queue"))


def test_shim_files_must_not_implement_model_routing() -> None:
    _assert_no_named_behavior(("route_model", "model_router", "select_model"))


def _assert_no_named_behavior(markers: tuple[str, ...]) -> None:
    for path, tree in _shim_trees():
        illegal = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                lowered = node.name.lower()
                if any(marker in lowered for marker in markers):
                    illegal.append(node.name)

        assert illegal == [], f"{_display(path)} implements forbidden behavior: {illegal}"


def _shim_trees() -> list[tuple[Path, ast.Module]]:
    return [(path, ast.parse(path.read_text(encoding="utf-8"), filename=str(path))) for path in _shim_files()]


def _shim_files() -> list[Path]:
    return list(SHIM_FILES)


def _import_targets(tree: ast.AST) -> list[str]:
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def _without_module_docstring(nodes: list[ast.stmt]) -> list[ast.stmt]:
    if nodes and isinstance(nodes[0], ast.Expr) and isinstance(nodes[0].value, ast.Constant):
        if isinstance(nodes[0].value.value, str):
            return nodes[1:]
    return nodes


def _call_name(func: ast.expr) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _is_router_like(node: ast.expr) -> bool:
    if isinstance(node, ast.Name):
        lowered = node.id.lower()
        return lowered == "router" or lowered.endswith("_router")
    if isinstance(node, ast.Attribute):
        return _is_router_like(node.value)
    return False


def _display(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT))

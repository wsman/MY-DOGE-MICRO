"""Guardrails for bootstrap container ownership."""

from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
BOOTSTRAP_ROOT = PROJECT_ROOT / "src" / "doge" / "bootstrap"


def test_only_process_root_constructs_sibling_containers() -> None:
    allowed_path = BOOTSTRAP_ROOT / "processes.py"
    forbidden_calls = {"RuntimeContainer", "GatewayContainer", "WorkspaceContainer"}

    for path in BOOTSTRAP_ROOT.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        calls = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        illegal = sorted(calls & forbidden_calls)
        if path == allowed_path:
            assert illegal == sorted(forbidden_calls)
        else:
            assert illegal == [], f"{path.name} must not construct sibling containers: {illegal}"


def test_bootstrap_containers_do_not_keep_private_cross_builders() -> None:
    for name in ("runtime.py", "gateway.py", "workspace.py"):
        source = (BOOTSTRAP_ROOT / name).read_text(encoding="utf-8")
        assert "def _gateway" not in source
        assert "def _workspace" not in source
        assert "def _runtime" not in source

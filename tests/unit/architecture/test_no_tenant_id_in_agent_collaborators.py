from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
AGENT_ROOT = PROJECT_ROOT / "src" / "doge" / "application" / "agent"

_ALLOWLIST = {
    "runtime_args.py",
    "runtime_kernel.py",
}


def test_agent_collaborators_do_not_add_raw_tenant_id_parameters() -> None:
    offenders: list[str] = []
    for path in sorted(AGENT_ROOT.glob("*.py")):
        if path.name in _ALLOWLIST:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for arg in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]:
                if arg.arg == "tenant_id":
                    relative = path.relative_to(PROJECT_ROOT).as_posix()
                    offenders.append(f"{relative}:{node.lineno} {node.name}")

    assert offenders == []

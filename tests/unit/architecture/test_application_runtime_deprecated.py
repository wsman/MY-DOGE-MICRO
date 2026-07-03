"""Guard: production code must not import the deprecated runtime facade.

ADR-0027 marks ``doge.application.runtime`` as a deprecated compatibility shim
in favor of ``doge.platform.runtime``. The shim package itself may re-export its
symbols, but no other production module under ``src/doge`` may import it. This
is a ratchet: the baseline is zero production importers, so any new offender
fails immediately.
"""

from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DOGE = PROJECT_ROOT / "src" / "doge"


def test_no_production_imports_of_deprecated_application_runtime() -> None:
    offenders: list[str] = []
    for path in SRC_DOGE.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(SRC_DOGE)
        # The shim package itself (application/runtime/**) is allowed to re-export.
        if rel.parts[:2] == ("application", "runtime"):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        modules: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                modules.append(node.module)
            elif isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
        for module in modules:
            if module == "doge.application.runtime" or module.startswith("doge.application.runtime."):
                offenders.append(f"{path.relative_to(PROJECT_ROOT)} imports {module}")
    assert offenders == [], (
        "doge.application.runtime is ADR-0027 deprecated; use doge.platform.runtime instead: "
        + "; ".join(offenders)
    )

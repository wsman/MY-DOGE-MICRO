"""Validate import boundaries: production code must not import compatibility shims.

Enforces ADR-0027 and ``docs/architecture/file-structure-policy.md``: new
platform code under ``src/doge/`` must import the canonical modules
(``doge.interfaces.gateway.routers``, ``doge.application.tools``), not the
compatibility shims (``doge.interfaces.api.routers.v1``,
``doge.application.agent.tools``).

The shim files themselves (and the whole ``routers/v1`` shim package) are
excluded — they are the re-export surfaces, not offenders.

This is a ratchet with a zero baseline: the clean tree has no production
importers of these shims, so any new offender fails immediately.
"""
from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
SCAN_PACKAGE_ROOT = SRC_ROOT / "doge"

# Absolute module prefixes that production code must not import. An import
# matches if the resolved module equals the prefix or starts with ``prefix + "."``.
FORBIDDEN_PREFIXES = (
    "doge.interfaces.api.routers.v1",
    "doge.application.agent.tools",
)

# The shim re-export surfaces themselves: excluded from the scan.
SHIM_FILES = {
    SCAN_PACKAGE_ROOT / "application" / "agent" / "tools.py",
    SCAN_PACKAGE_ROOT / "interfaces" / "api" / "routers" / "__init__.py",
}
SHIM_DIRS = ()


@dataclass(frozen=True)
class Finding:
    path: Path
    module: str

    def format(self) -> str:
        return (
            f"{_display(self.path)}: imports forbidden compatibility shim "
            f"'{self.module}'; import the canonical module instead "
            f"(doge.interfaces.gateway.routers / doge.application.tools)"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--warn-only", action="store_true")
    args = parser.parse_args(argv)

    findings = validate()
    if findings:
        for finding in findings:
            print(finding.format())
        return 0 if args.warn_only else 1
    print("import boundary validation passed")
    return 0


def validate(root: Path = ROOT) -> list[Finding]:
    findings: list[Finding] = []
    scan_root = (root / "src" / "doge") if root != ROOT else SCAN_PACKAGE_ROOT
    shim_files = {(root / "src" / "doge" / "application" / "agent" / "tools.py")}
    shim_files.add(root / "src" / "doge" / "interfaces" / "api" / "routers" / "__init__.py")
    shim_dirs = [root / "src" / "doge" / "interfaces" / "api" / "routers" / "v1"]
    for path in sorted(scan_root.rglob("*.py")):
        if _is_shim(path, shim_files, shim_dirs):
            continue
        if "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError:
            # A syntax error is a separate failure; do not mask it silently.
            findings.append(Finding(path, "<unparseable>"))
            continue
        pkg_parts = _package_parts(path, root)
        for module in _imported_modules(tree, pkg_parts):
            if _is_forbidden(module):
                findings.append(Finding(path, module))
    return findings


def _is_shim(path: Path, shim_files: set[Path], shim_dirs: list[Path]) -> bool:
    resolved = path.resolve()
    if resolved in {p.resolve() for p in shim_files}:
        return True
    for d in shim_dirs:
        try:
            resolved.relative_to(d.resolve())
            return True
        except ValueError:
            continue
    return False


def _package_parts(path: Path, root: Path) -> list[str]:
    """Return the dotted package containing ``path`` (e.g. doge.application.agent)."""
    rel = path.relative_to(root / "src")  # doge/application/agent/tools.py
    parts = list(rel.parts)[:-1]  # drop the file -> (doge, application, agent)
    return [p for p in parts]


def _imported_modules(tree: ast.AST, pkg_parts: list[str]) -> list[str]:
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                out.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            resolved = _resolve_relative(pkg_parts, node.level, node.module)
            if resolved is not None:
                out.append(resolved)
    return out


def _resolve_relative(pkg_parts: list[str], level: int, module: str | None) -> str | None:
    """Resolve a ``from ... import`` to its absolute module string.

    ``level`` 0 means absolute (``module`` is already absolute). ``level`` >= 1
    is relative: level 1 is the current package, level 2 its parent, etc.
    """
    if level == 0:
        return module
    # Up (level - 1) levels from the current package.
    drop = level - 1
    if drop > len(pkg_parts):
        return module  # cannot resolve reliably; leave as-is (won't match doge.*)
    base = pkg_parts[: len(pkg_parts) - drop]
    if module:
        return ".".join(base + [module]) if base else module
    return ".".join(base)


def _is_forbidden(module: str) -> bool:
    for prefix in FORBIDDEN_PREFIXES:
        if module == prefix or module.startswith(prefix + "."):
            return True
    return False


def _display(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


if __name__ == "__main__":
    sys.exit(main())

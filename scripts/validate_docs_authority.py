"""Guard reader-facing docs against new duplicate documentation authorities."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

CANONICAL_AUTHORITY_PATHS = {
    "bounded_contexts": Path("docs/architecture/overview.md"),
    "runtime_path": Path("docs/architecture/runtime-contracts.md"),
    "shim_rules": Path("docs/architecture/file-structure-policy.md"),
}

GENERATED_OR_DECISION_PATTERNS = (
    "docs/architecture/adr-*.md",
    "docs/archive/**/*.md",
    "docs/progress/*.md",
    "docs/quality/status.md",
)

BASELINE_ALLOWED_RESTATEMENTS = {
    Path("docs/GETTING_STARTED.md"),
    Path("docs/architecture/architecture-traceability.md"),
    Path("docs/architecture/compatibility-surfaces.md"),
    Path("docs/architecture/control-manifest.md"),
    Path("docs/architecture/module-boundaries.md"),
    Path("docs/architecture/runtime-levels.md"),
    Path("docs/product/overview.md"),
    Path("docs/product/user-scenarios.md"),
    Path("docs/reference/module-map.md"),
}

BOUNDED_CONTEXT_NAMES = (
    "Market Intelligence",
    "Research",
    "Portfolio & Risk",
    "Quant & Data Lab",
    "Workspace & Workflow",
    "Agent Runtime",
    "Knowledge & Evidence",
    "Governance & Evaluation",
)

REFERENCE_SHORTCUTS = {
    Path("docs/reference/api.md"): "http_api",
    Path("docs/reference/http-api.md"): "http_api",
    Path("docs/reference/cli.md"): "cli",
    Path("docs/reference/mcp.md"): "mcp_tools",
    Path("docs/reference/tools.md"): "mcp_tools",
    Path("docs/reference/env-vars.md"): "env_vars",
}


@dataclass(frozen=True)
class Finding:
    path: Path
    fact: str
    message: str

    def format(self) -> str:
        return f"{_display(self.path)}: {self.fact}: {self.message}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--warn-only", action="store_true")
    args = parser.parse_args(argv)

    findings = validate()
    if findings:
        for finding in findings:
            print(finding.format())
        return 0 if args.warn_only else 1
    print("docs authority validation passed")
    return 0


def validate(root: Path = ROOT) -> list[Finding]:
    findings: list[Finding] = []
    for path in _collect_markdown(root):
        rel = _relative(path, root)
        if _is_allowed_restatement(rel):
            continue
        text = path.read_text(encoding="utf-8")
        findings.extend(_validate_text(rel, path, text))
    return findings


def _validate_text(rel: Path, path: Path, text: str) -> list[Finding]:
    findings: list[Finding] = []
    if _restates_bounded_contexts(text):
        findings.append(
            Finding(
                path,
                "bounded_contexts",
                "link to docs/architecture/overview.md instead of re-listing the eight bounded contexts",
            )
        )
    if _restates_runtime_path(text):
        findings.append(
            Finding(
                path,
                "runtime_path",
                "link to docs/architecture/runtime-contracts.md instead of restating the canonical runtime path",
            )
        )
    if _restates_shim_rules(text):
        findings.append(
            Finding(
                path,
                "shim_rules",
                "link to docs/architecture/file-structure-policy.md instead of restating shim behavior rules",
            )
        )
    findings.extend(_validate_reference_shortcut(rel, path, text))
    return findings


def _validate_reference_shortcut(rel: Path, path: Path, text: str) -> list[Finding]:
    shortcut_type = REFERENCE_SHORTCUTS.get(rel)
    if shortcut_type is None:
        return []

    if shortcut_type == "http_api" and _copies_http_route_table(text):
        return [
            Finding(
                path,
                "reference_http_table",
                "link to docs/API.md instead of copying the HTTP route table into a reference shortcut",
            )
        ]
    if shortcut_type == "cli" and _copies_cli_command_table(text):
        return [
            Finding(
                path,
                "reference_cli_table",
                "link to docs/CLI.md instead of copying the CLI command table into a reference shortcut",
            )
        ]
    if shortcut_type == "mcp_tools" and _copies_mcp_tool_table(text):
        return [
            Finding(
                path,
                "reference_tool_table",
                "link to docs/MCP_SERVER.md instead of copying the MCP tool catalog into a reference shortcut",
            )
        ]
    if shortcut_type == "env_vars" and _copies_env_var_table(text):
        return [
            Finding(
                path,
                "reference_env_table",
                "link to configuration and setup authorities instead of copying an environment-variable table",
            )
        ]
    return []


def _collect_markdown(root: Path) -> list[Path]:
    paths = [root / "README.md"]
    paths.extend((root / "docs").glob("**/*.md"))
    return sorted(path for path in paths if path.is_file())


def _is_allowed_restatement(rel: Path) -> bool:
    if rel in CANONICAL_AUTHORITY_PATHS.values():
        return True
    if rel in BASELINE_ALLOWED_RESTATEMENTS:
        return True
    for pattern in GENERATED_OR_DECISION_PATTERNS:
        if rel.match(pattern):
            return True
    return False


def _restates_bounded_contexts(text: str) -> bool:
    hits = sum(1 for name in BOUNDED_CONTEXT_NAMES if name in text)
    return hits >= 6


def _restates_runtime_path(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text.lower())
    has_route = "/v1" in normalized
    has_sdk = "sdk" in normalized
    has_persisted_runtime = "persisted runtime" in normalized
    has_process_root = "process roots" in normalized or "doge.bootstrap.processes" in normalized
    return has_process_root and has_persisted_runtime and has_route and has_sdk


def _restates_shim_rules(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text.lower())
    if "shim sunset rules" in normalized:
        return True
    return (
        "may re-export" in normalized
        and "delegate" in normalized
        and "warn" in normalized
        and ("must not add" in normalized or "may not add" in normalized)
    )


def _copies_http_route_table(text: str) -> bool:
    if _table_with_header(text, ("method",), ("path", "endpoint"), min_rows=3):
        return True
    route_hits = 0
    for line in text.splitlines():
        if re.search(r"\|\s*(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)\s+/", line):
            route_hits += 1
    return route_hits >= 3


def _copies_cli_command_table(text: str) -> bool:
    if _table_with_header(text, ("command",), min_rows=3):
        return True
    if _table_with_header(text, ("flag",), min_rows=3):
        return True
    return _table_with_header(text, ("option",), min_rows=3)


def _copies_mcp_tool_table(text: str) -> bool:
    if _table_with_header(text, ("tool",), min_rows=3):
        return True
    tool_rows = 0
    for line in text.splitlines():
        if line.startswith("|") and re.search(r"`[a-z0-9_]+`", line, re.IGNORECASE):
            if "tool" in line.lower() or "mcp" in line.lower():
                tool_rows += 1
    return tool_rows >= 3


def _copies_env_var_table(text: str) -> bool:
    if _table_with_header(text, ("environment",), min_rows=3):
        return True
    return _table_with_header(text, ("variable",), min_rows=3)


def _table_with_header(
    text: str,
    required_terms: tuple[str, ...],
    optional_terms: tuple[str, ...] = (),
    *,
    min_rows: int,
) -> bool:
    for table in _markdown_tables(text):
        if len(table) < min_rows + 2:
            continue
        header = table[0].lower()
        if not all(term in header for term in required_terms):
            continue
        if optional_terms and not any(term in header for term in optional_terms):
            continue
        return True
    return False


def _markdown_tables(text: str) -> list[list[str]]:
    tables: list[list[str]] = []
    current: list[str] = []
    for line in text.splitlines():
        if line.startswith("|"):
            current.append(line)
            continue
        if current:
            tables.append(current)
            current = []
    if current:
        tables.append(current)
    return tables


def _relative(path: Path, root: Path) -> Path:
    return path.resolve().relative_to(root.resolve())


def _display(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


if __name__ == "__main__":
    sys.exit(main())

"""Validate reader-path and guide docs keep useful structure."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC_DIRS = (
    ROOT / "docs" / "start-here",
    ROOT / "docs" / "guides",
)

REQUIRED_SECTIONS = (
    "## Your 3-step first path",
    "## When To Leave This Page",
)

CANONICAL_LINK_TARGETS = (
    "../API.md",
    "../CLI.md",
    "../MCP_SERVER.md",
    "../GETTING_STARTED.md",
    "../operations-runbook.md",
    "../architecture/",
    "../quality/status.md",
    "../progress/runtime-maturity.yaml",
    "../demo/",
    "../../packages/",
)


@dataclass(frozen=True)
class Finding:
    path: Path
    message: str

    def format(self) -> str:
        return f"{_display(self.path)}: {self.message}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--warn-only", action="store_true")
    args = parser.parse_args(argv)

    findings = validate()
    if findings:
        for finding in findings:
            print(finding.format())
        return 0 if args.warn_only else 1
    print("docs guide structure validation passed")
    return 0


def validate(paths: list[Path] | None = None) -> list[Finding]:
    findings: list[Finding] = []
    for path in paths or _collect_paths():
        findings.extend(validate_file(path))
    return findings


def validate_file(path: Path) -> list[Finding]:
    text = path.read_text(encoding="utf-8")
    findings: list[Finding] = []
    if not text.startswith("# "):
        findings.append(Finding(path, "document must start with a single H1 heading"))
    for section in REQUIRED_SECTIONS:
        if section not in text:
            findings.append(Finding(path, f"missing required section {section!r}"))
    if not _has_canonical_link(text):
        findings.append(Finding(path, "missing link to a canonical reference, architecture, status, demo, or SDK source"))
    if text.count("\n") < 20:
        findings.append(Finding(path, "reader-path docs must contain enough guidance to be more than a redirect"))
    return findings


def _collect_paths() -> list[Path]:
    paths: list[Path] = []
    for directory in DOC_DIRS:
        if directory.exists():
            paths.extend(sorted(directory.glob("*.md")))
    return paths


def _has_canonical_link(text: str) -> bool:
    return any(target in text for target in CANONICAL_LINK_TARGETS)


def _display(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


if __name__ == "__main__":
    sys.exit(main())

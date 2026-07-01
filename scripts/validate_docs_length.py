"""Validate documentation length caps for reader-path docs and redirect stubs."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
START_HERE_DIR = ROOT / "docs" / "start-here"
GUIDES_DIR = ROOT / "docs" / "guides"
REDIRECT_STUBS = (
    ROOT / "docs" / "reference" / "api.md",
    ROOT / "docs" / "reference" / "cli.md",
    ROOT / "docs" / "reference" / "mcp.md",
    ROOT / "docs" / "reference" / "tools.md",
    ROOT / "docs" / "reference" / "env-vars.md",
    ROOT / "docs" / "reference" / "sdk-python.md",
    ROOT / "docs" / "reference" / "sdk-typescript.md",
)
SHORT_ENTRY_DOCS = (
    ROOT / "docs" / "progress" / "current-status.md",
    ROOT / "docs" / "architecture" / "canonical-runtime-path.md",
    ROOT / "docs" / "architecture" / "bounded-contexts.md",
    ROOT / "docs" / "architecture" / "data-ownership.md",
    ROOT / "docs" / "architecture" / "security-and-data-boundaries.md",
    ROOT / "docs" / "product" / "runtime-levels.md",
    ROOT / "docs" / "product" / "roadmap.md",
    ROOT / "docs" / "quality" / "eval-metrics.md",
    ROOT / "docs" / "quality" / "test-matrix.md",
    ROOT / "docs" / "quality" / "validation-scripts.md",
    ROOT / "docs" / "demo" / "kimi-sa-demo-script.md",
    ROOT / "docs" / "demo" / "solution-architecture-talk-track.md",
    ROOT / "docs" / "demo" / "demo-data.md",
    ROOT / "docs" / "demo" / "eval-storyboard.md",
    ROOT / "docs" / "demo" / "screenshots.md",
    ROOT / "docs" / "archive" / "old-module-docs" / "README.md",
    ROOT / "docs" / "archive" / "superseded" / "README.md",
)

START_HERE_MIN_LINES = 80
START_HERE_MAX_LINES = 120
GUIDE_SOFT_MAX_LINES = 250
GUIDE_HARD_MAX_LINES = 400
REDIRECT_MAX_LINES = 80
SHORT_ENTRY_MAX_LINES = 100

# Canonical long-form guides are contract-tested walkthroughs that exceed the
# scannable soft cap but stay under the hard cap. Exempt them from the soft cap
# only (e.g. docs/guides/getting-started.md, WAVE2-DOC-GETTING_STARTED).
CANONICAL_LONG_GUIDES = {
    ROOT / "docs" / "guides" / "getting-started.md",
}


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
    print("docs length validation passed")
    return 0


def validate() -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(_validate_start_here())
    findings.extend(_validate_guides())
    findings.extend(_validate_redirect_stubs())
    findings.extend(_validate_short_entry_docs())
    return findings


def _validate_start_here() -> list[Finding]:
    findings: list[Finding] = []
    if not START_HERE_DIR.exists():
        return findings
    for path in sorted(START_HERE_DIR.glob("*.md")):
        lines = _line_count(path)
        if lines < START_HERE_MIN_LINES or lines > START_HERE_MAX_LINES:
            findings.append(
                Finding(
                    path,
                    f"expected {START_HERE_MIN_LINES}-{START_HERE_MAX_LINES} lines for start-here docs, found {lines}",
                )
            )
    return findings


def _validate_guides() -> list[Finding]:
    findings: list[Finding] = []
    if not GUIDES_DIR.exists():
        return findings
    for path in sorted(GUIDES_DIR.glob("*.md")):
        lines = _line_count(path)
        if lines > GUIDE_HARD_MAX_LINES:
            findings.append(Finding(path, f"guide exceeds hard cap {GUIDE_HARD_MAX_LINES} lines: {lines}"))
        elif lines > GUIDE_SOFT_MAX_LINES and path not in CANONICAL_LONG_GUIDES:
            findings.append(Finding(path, f"guide exceeds soft cap {GUIDE_SOFT_MAX_LINES} lines: {lines}"))
    return findings


def _validate_redirect_stubs() -> list[Finding]:
    findings: list[Finding] = []
    for path in REDIRECT_STUBS:
        if not path.exists():
            findings.append(Finding(path, "redirect entry is missing"))
            continue
        lines = _line_count(path)
        if lines > REDIRECT_MAX_LINES:
            findings.append(Finding(path, f"redirect entry exceeds {REDIRECT_MAX_LINES} lines: {lines}"))
    return findings


def _validate_short_entry_docs() -> list[Finding]:
    findings: list[Finding] = []
    for path in SHORT_ENTRY_DOCS:
        if not path.exists():
            findings.append(Finding(path, "short entry doc is missing"))
            continue
        lines = _line_count(path)
        if lines > SHORT_ENTRY_MAX_LINES:
            findings.append(Finding(path, f"short entry doc exceeds {SHORT_ENTRY_MAX_LINES} lines: {lines}"))
    return findings


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def _display(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


if __name__ == "__main__":
    sys.exit(main())

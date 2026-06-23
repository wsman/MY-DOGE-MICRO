"""Validate current docs do not regress to stale architecture counts."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHITECTURE = ROOT / "docs" / "registry" / "architecture.yaml"
MATURITY = ROOT / "docs" / "progress" / "runtime-maturity.yaml"

CURRENT_DOCS = [
    ROOT / "README.md",
    ROOT / "docs" / "index.md",
    ROOT / "docs" / "product" / "overview.md",
    ROOT / "docs" / "architecture" / "overview.md",
    ROOT / "docs" / "reference" / "api.md",
    ROOT / "docs" / "reference" / "cli.md",
    ROOT / "docs" / "reference" / "mcp.md",
    ROOT / "docs" / "reference" / "configuration.md",
    ROOT / "docs" / "operations" / "local-deployment.md",
    ROOT / "docs" / "progress" / "README.md",
    ROOT / "docs" / "quality" / "status.md",
]

STALE_PATTERNS = [
    "MY-DOGE QUANT SYSTEM",
    "15 modules",
    "20 product modules",
    "51 product routes",
    "Macro/Micro three-layer",
    "三层架构",
]

EXPECTED_ARCHIVE_FILES = {
    "adr-0016-0020-disposition-review-2026-06-23.md",
    "adr-0021-0022-review-2026-06-23.md",
    "alpha-magical-peach-completion-audit-2026-06-23.md",
    "alpha-magical-peach-pre-remote-ci-package-2026-06-23.md",
    "external-gate-next-actions-2026-06-23.md",
    "feature-flag-deprecation-plan-2026-06-23.md",
    "platformization-consolidation-phase-a-2026-06-23.md",
    "platformization-consolidation-phase-b-2026-06-23.md",
    "platformization-consolidation-phase-c-2026-06-23.md",
    "platformization-consolidation-phase-d-2026-06-23.md",
    "platformization-consolidation-phase-e-runtime-2026-06-23.md",
    "platformization-consolidation-phase-f-web-2026-06-23.md",
    "remote-ci-handoff-2026-06-23.md",
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
    print("docs stale-count validation passed")
    return 0


def validate() -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(_validate_current_docs())
    findings.extend(_validate_architecture_registry())
    findings.extend(_validate_archive_location())
    findings.extend(_validate_maturity_posture())
    return findings


def _validate_current_docs() -> list[Finding]:
    findings: list[Finding] = []
    for path in CURRENT_DOCS:
        if not path.exists():
            findings.append(Finding(path, "current documentation file is missing"))
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in STALE_PATTERNS:
            if pattern in text:
                findings.append(Finding(path, f"stale current-doc phrase found: {pattern!r}"))
    return findings


def _validate_architecture_registry() -> list[Finding]:
    text = ARCHITECTURE.read_text(encoding="utf-8")
    systems = _parse_block_count(text, "systems")
    superseded = _parse_block_count(text, "superseded_systems")
    findings: list[Finding] = []
    if systems != 8:
        findings.append(Finding(ARCHITECTURE, f"expected 8 active systems, found {systems}"))
    if superseded != 20:
        findings.append(Finding(ARCHITECTURE, f"expected 20 superseded systems, found {superseded}"))
    if "status: \"superseded_by: ADR-0021\"" not in text:
        findings.append(Finding(ARCHITECTURE, "superseded systems must cite ADR-0021"))
    if "status: \"superseded_by: ADR-0022\"" in text:
        findings.append(Finding(ARCHITECTURE, "old module supersession must not be attributed to ADR-0022"))
    return findings


def _validate_archive_location() -> list[Finding]:
    progress = ROOT / "docs" / "progress"
    archive = ROOT / "docs" / "archive" / "audits"
    findings: list[Finding] = []
    progress_hits = {path.name for path in progress.glob("*2026-06-23.md")}
    if progress_hits:
        findings.append(Finding(progress, f"dated 2026-06-23 audits still in progress: {sorted(progress_hits)}"))
    archived = {path.name for path in archive.glob("*2026-06-23.md")}
    missing = EXPECTED_ARCHIVE_FILES - archived
    extra = archived - EXPECTED_ARCHIVE_FILES
    if missing:
        findings.append(Finding(archive, f"missing archived audit files: {sorted(missing)}"))
    if extra:
        findings.append(Finding(archive, f"unexpected archived audit files: {sorted(extra)}"))
    return findings


def _validate_maturity_posture() -> list[Finding]:
    text = MATURITY.read_text(encoding="utf-8")
    findings: list[Finding] = []
    if not re.search(r"\bproduction_ready:\s*false\b", text):
        findings.append(Finding(MATURITY, "production_ready must remain false"))
    if not re.search(r"\bstable_declaration:\s*forbidden\b", text):
        findings.append(Finding(MATURITY, "stable_declaration must remain forbidden"))
    return findings


def _parse_block_count(text: str, key: str) -> int:
    in_block = False
    count = 0
    for line in text.splitlines():
        if not in_block:
            if line == f"{key}:":
                in_block = True
            continue
        if line and not line.startswith(" ") and not line.startswith("#"):
            break
        if line.strip().startswith("- {"):
            count += 1
    return count


def _display(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


if __name__ == "__main__":
    sys.exit(main())

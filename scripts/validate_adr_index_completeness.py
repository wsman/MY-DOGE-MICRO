"""Validate every architecture ADR file is listed in architecture.yaml."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHITECTURE_DIR = ROOT / "docs" / "architecture"
REGISTRY = ROOT / "docs" / "registry" / "architecture.yaml"

ADR_FILE_RE = re.compile(r"adr-(\d{4})-.*\.md$")
ADR_INDEX_RE = re.compile(r"^\s*-\s+id:\s+(ADR-\d{4})\b", re.MULTILINE)


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
    print("ADR index completeness validation passed")
    return 0


def validate(
    architecture_dir: Path = ARCHITECTURE_DIR,
    registry: Path = REGISTRY,
) -> list[Finding]:
    indexed = _indexed_adr_ids(registry)
    findings: list[Finding] = []
    for adr_file in sorted(architecture_dir.glob("adr-*.md")):
        match = ADR_FILE_RE.match(adr_file.name)
        if not match:
            continue
        adr_id = f"ADR-{match.group(1)}"
        if adr_id not in indexed:
            findings.append(Finding(adr_file, f"{adr_id} is missing from adr_index"))
    return findings


def _indexed_adr_ids(registry: Path) -> set[str]:
    text = registry.read_text(encoding="utf-8")
    return set(ADR_INDEX_RE.findall(text))


def _display(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


if __name__ == "__main__":
    sys.exit(main())

"""Validate compatibility-surface registry sunset columns stay actionable."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs" / "architecture" / "compatibility-surfaces.md"
REQUIRED_COLUMNS = ("surface", "parity_tests", "earliest_removal")
PLACEHOLDERS = {"", "-", "tbd", "todo", "none", "n/a", "na"}


@dataclass(frozen=True)
class Finding:
    path: Path
    surface: str
    message: str

    def format(self) -> str:
        return f"{_display(self.path)}: {self.surface}: {self.message}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--warn-only", action="store_true")
    args = parser.parse_args(argv)

    findings = validate()
    if findings:
        for finding in findings:
            print(finding.format())
        return 0 if args.warn_only else 1
    print("compatibility surface sunset validation passed")
    return 0


def validate(path: Path = REGISTRY) -> list[Finding]:
    text = path.read_text(encoding="utf-8")
    rows = _surface_rows(text)
    findings: list[Finding] = []
    if not rows:
        return [Finding(path, "<registry>", "surface registry table is missing")]

    headers = rows[0]
    missing = [column for column in REQUIRED_COLUMNS if column not in headers]
    if missing:
        return [Finding(path, "<registry>", f"missing required columns: {', '.join(missing)}")]

    column_indexes = {column: headers.index(column) for column in REQUIRED_COLUMNS}
    for row in rows[1:]:
        if len(row) != len(headers):
            findings.append(Finding(path, row[0] if row else "<row>", "row has wrong number of cells"))
            continue
        surface = row[column_indexes["surface"]]
        for column in ("parity_tests", "earliest_removal"):
            value = row[column_indexes[column]].strip().lower()
            if value in PLACEHOLDERS:
                findings.append(Finding(path, surface, f"{column} must name concrete gates"))
    return findings


def _surface_rows(text: str) -> list[list[str]]:
    lines = text.splitlines()
    rows: list[list[str]] = []
    in_table = False
    for line in lines:
        if line.strip() == "## Surface Registry":
            in_table = True
            continue
        if in_table and line.startswith("## "):
            break
        if not in_table or not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if set(cells) == {"---"}:
            continue
        rows.append(cells)
    return rows


def _display(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


if __name__ == "__main__":
    sys.exit(main())

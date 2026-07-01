"""Validate new-module header template and optional module header blocks."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "new-module-header.md"
PR_CHECKLIST = ROOT / "docs" / "architecture" / "pr-checklist.md"

REQUIRED_FIELDS = (
    "Canonical owner:",
    "Bounded context:",
    "Allowed imports:",
    "Forbidden imports:",
    "Public contract:",
    "Maturity:",
)

ALLOWED_CONTEXTS = {
    "Market Intelligence",
    "Research",
    "Portfolio & Risk",
    "Quant & Data Lab",
    "Workspace & Workflow",
    "Agent Runtime",
    "Knowledge & Evidence",
    "Governance & Evaluation",
}


@dataclass(frozen=True)
class Finding:
    path: Path
    message: str

    def format(self) -> str:
        return f"{_display(self.path)}: {self.message}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", action="append", default=[], help="new file to enforce header fields against")
    parser.add_argument("--warn-only", action="store_true", help="report findings without failing")
    args = parser.parse_args(argv)

    findings = validate_template_files()
    for raw in args.file:
        findings.extend(validate_module_file(Path(raw)))

    if findings:
        for finding in findings:
            print(finding.format())
        return 0 if args.warn_only else 1
    print("module header validation passed")
    return 0


def validate_template_files() -> list[Finding]:
    findings: list[Finding] = []
    for path in (TEMPLATE, PR_CHECKLIST):
        if not path.exists():
            findings.append(Finding(path, "required governance artifact is missing"))
    if TEMPLATE.exists():
        text = TEMPLATE.read_text(encoding="utf-8")
        for field in REQUIRED_FIELDS:
            if field not in text:
                findings.append(Finding(TEMPLATE, f"template missing field {field!r}"))
    if PR_CHECKLIST.exists():
        text = PR_CHECKLIST.read_text(encoding="utf-8")
        for needle in ("canonical owner", "compatibility surfaces", "Production Ready"):
            if needle not in text:
                findings.append(Finding(PR_CHECKLIST, f"checklist missing {needle!r}"))
    return findings


def validate_module_file(path: Path) -> list[Finding]:
    text = path.read_text(encoding="utf-8")
    findings: list[Finding] = []
    for field in REQUIRED_FIELDS:
        if field not in text:
            findings.append(Finding(path, f"module header missing field {field!r}"))
    context = _field_value(text, "Bounded context:")
    if context and context not in ALLOWED_CONTEXTS:
        findings.append(Finding(path, f"unknown bounded context {context!r}"))
    return findings


def _field_value(text: str, field: str) -> str | None:
    for line in text.splitlines():
        if line.strip().startswith(field):
            return line.split(field, 1)[1].strip() or None
    return None


def _display(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


if __name__ == "__main__":
    sys.exit(main())

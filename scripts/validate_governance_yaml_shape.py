"""Lightweight governance YAML shape validator.

This intentionally does not claim to be a full YAML parser. It gives the
closure runbook a repeatable local check in environments where PyYAML is not
installed: file presence, UTF-8 decoding, no tab indentation, no CR-only line
endings, even two-space indentation, unique top-level keys, and expected
top-level sections for the governance YAML files touched by the Kimi closure.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_FILES = [
    Path("docs/progress/runtime-maturity.yaml"),
    Path("production/sprint-status.yaml"),
    Path("docs/registry/architecture.yaml"),
    Path("docs/registry/entities.yaml"),
    Path("docs/architecture/tr-registry.yaml"),
]

REQUIRED_TOP_LEVEL_KEYS = {
    Path("docs/progress/runtime-maturity.yaml"): {
        "generated_at",
        "stable_declaration",
        "maturity_labels",
        "local_verification",
    },
    Path("production/sprint-status.yaml"): {
        "version",
        "last_updated",
        "sprints",
        "rollup",
    },
    Path("docs/registry/architecture.yaml"): {
        "version",
        "last_updated",
        "systems",
        "adr_index",
    },
    Path("docs/registry/entities.yaml"): {
        "version",
        "last_updated",
        "formulas",
        "constants",
        "entities",
    },
    Path("docs/architecture/tr-registry.yaml"): {
        "version",
        "last_updated",
        "requirements",
    },
}

TOP_LEVEL_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):(?:\s|$)")


@dataclass(frozen=True)
class Finding:
    path: str
    line: int | None
    message: str

    def to_dict(self) -> dict[str, object]:
        return {"path": self.path, "line": self.line, "message": self.message}


def validate_file(path: Path, *, required_keys: set[str] | None = None) -> list[Finding]:
    """Validate one YAML-like governance file without importing PyYAML."""

    display = _display_path(path)
    findings: list[Finding] = []
    if not path.exists():
        return [Finding(display, None, "file does not exist")]
    raw = path.read_bytes()
    if not raw:
        findings.append(Finding(display, None, "file is empty"))
        return findings
    findings.extend(_cr_only_findings(raw, display))
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        return [Finding(display, None, f"file is not UTF-8: {exc}")]

    top_level_seen: dict[str, int] = {}
    for line_no, line in enumerate(text.splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if "\t" in line:
            findings.append(Finding(display, line_no, "tabs are not allowed in governance YAML"))
        indent = len(line) - len(line.lstrip(" "))
        if indent % 2:
            findings.append(Finding(display, line_no, "indentation must use even two-space steps"))
        if indent == 0:
            match = TOP_LEVEL_KEY_RE.match(line)
            if match:
                key = match.group(1)
                if key in top_level_seen:
                    findings.append(
                        Finding(
                            display,
                            line_no,
                            f"duplicate top-level key {key!r}; first seen on line {top_level_seen[key]}",
                        )
                    )
                else:
                    top_level_seen[key] = line_no

    missing = sorted((required_keys or set()) - set(top_level_seen))
    for key in missing:
        findings.append(Finding(display, None, f"missing required top-level key {key!r}"))
    return findings


def validate_files(paths: Iterable[Path]) -> dict[str, object]:
    """Validate all requested files and return a JSON-serializable payload."""

    files = []
    all_findings: list[Finding] = []
    for input_path in paths:
        resolved = input_path if input_path.is_absolute() else ROOT / input_path
        relative = _relative_key(resolved)
        findings = validate_file(resolved, required_keys=REQUIRED_TOP_LEVEL_KEYS.get(relative))
        all_findings.extend(findings)
        files.append(
            {
                "path": _display_path(resolved),
                "required_top_level_keys": sorted(REQUIRED_TOP_LEVEL_KEYS.get(relative, set())),
                "findings": [finding.to_dict() for finding in findings],
                "passed": not findings,
            }
        )
    return {
        "schema": "doge.governance_yaml_shape.v1",
        "passed": not all_findings,
        "summary": {"files": len(files), "findings": len(all_findings)},
        "files": files,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="YAML files to validate. Defaults to the Kimi closure governance YAML set.",
    )
    args = parser.parse_args(argv)
    payload = validate_files(args.paths or DEFAULT_FILES)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["passed"] else 1


def _cr_only_findings(raw: bytes, display: str) -> list[Finding]:
    findings: list[Finding] = []
    line = 1
    index = 0
    while index < len(raw):
        byte = raw[index]
        if byte == 10:
            line += 1
            index += 1
            continue
        if byte == 13:
            if index + 1 >= len(raw) or raw[index + 1] != 10:
                findings.append(Finding(display, line, "CR-only line ending is not allowed"))
                line += 1
                index += 1
                continue
            line += 1
            index += 2
            continue
        index += 1
    return findings


def _relative_key(path: Path) -> Path:
    try:
        return path.resolve().relative_to(ROOT)
    except ValueError:
        return path


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    sys.exit(main())

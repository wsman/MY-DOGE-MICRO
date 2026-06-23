"""Validate internal Markdown links for current documentation entrypoints."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_PATTERNS = [
    "README.md",
    "docs/index.md",
    "docs/product/*.md",
    "docs/architecture/*.md",
    "docs/reference/*.md",
    "docs/operations/*.md",
    "docs/quality/*.md",
    "docs/progress/README.md",
    "design/cdd/bc-*.md",
    "design/cdd/module-index.md",
]

ARCHIVE_PATTERNS = [
    "docs/archive/**/*.md",
]

LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


@dataclass(frozen=True)
class Finding:
    path: Path
    target: str
    message: str

    def format(self) -> str:
        return f"{_display(self.path)} -> {self.target}: {self.message}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--include-archive", action="store_true")
    parser.add_argument("--warn-only", action="store_true")
    args = parser.parse_args(argv)

    paths = _collect_paths(include_archive=args.include_archive)
    findings: list[Finding] = []
    for path in paths:
        findings.extend(validate_file(path))

    if findings:
        for finding in findings:
            print(finding.format())
        return 0 if args.warn_only else 1

    print(f"validated {len(paths)} markdown files")
    return 0


def validate_file(path: Path) -> list[Finding]:
    text = path.read_text(encoding="utf-8")
    findings: list[Finding] = []
    for raw_target in LINK_RE.findall(text):
        target = raw_target.strip()
        if not _is_local_target(target):
            continue
        clean = _strip_anchor(target)
        if not clean:
            continue
        clean = unquote(clean).strip("<>")
        candidate = (path.parent / clean).resolve()
        if not _stays_in_repo(candidate):
            findings.append(Finding(path, target, "target escapes repository"))
            continue
        if not candidate.exists():
            findings.append(Finding(path, target, "target does not exist"))
    return findings


def _collect_paths(*, include_archive: bool) -> list[Path]:
    patterns = list(DEFAULT_PATTERNS)
    if include_archive:
        patterns.extend(ARCHIVE_PATTERNS)
    paths: set[Path] = set()
    for pattern in patterns:
        paths.update(path for path in ROOT.glob(pattern) if path.is_file())
    return sorted(paths)


def _is_local_target(target: str) -> bool:
    lower = target.lower()
    if lower.startswith(("http://", "https://", "mailto:", "tel:")):
        return False
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target):
        return False
    return True


def _strip_anchor(target: str) -> str:
    return target.split("#", 1)[0]


def _stays_in_repo(path: Path) -> bool:
    try:
        path.relative_to(ROOT.resolve())
        return True
    except ValueError:
        return False


def _display(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


if __name__ == "__main__":
    sys.exit(main())

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Mapping


ROOT = Path(__file__).resolve().parents[1]
PLAN = Path(r"C:\Users\Aby\.claude\plans\alpha-magical-peach.md")

DEFAULT_FILES = [
    PLAN,
    ROOT / "docs" / "progress" / "runtime-maturity.yaml",
    ROOT / "docs" / "progress" / "remote-ci-handoff-2026-06-23.md",
    ROOT / "docs" / "progress" / "alpha-magical-peach-completion-audit-2026-06-23.md",
    ROOT / "docs" / "progress" / "alpha-magical-peach-pre-remote-ci-package-2026-06-23.md",
    ROOT / "docs" / "progress" / "external-gate-next-actions-2026-06-23.md",
    ROOT / "docs" / "progress" / "adr-0016-0020-disposition-review-2026-06-23.md",
    ROOT / "production" / "sprints" / "sprint-017-external-validation-and-provider-hardening.md",
]

REQUIRED_SNIPPETS = {
    str(PLAN): [
        "has not reached enterprise Beta or Production / GA",
        "It must not be described as:",
        "production_ready: false",
        "stable_declaration: forbidden",
        "Level 3 `experimental`",
        "Enterprise Beta can be reconsidered only after:",
    ],
    "docs/progress/runtime-maturity.yaml": [
        "stable_declaration: forbidden",
        "level_3_sdk_platform: experimental",
        "production_ready: false",
    ],
    "docs/progress/remote-ci-handoff-2026-06-23.md": [
        "it is not sufficient for enterprise Beta or Production",
        "production_ready: false",
        "stable_declaration: forbidden",
        "level_3_sdk_platform: experimental",
    ],
    "docs/progress/alpha-magical-peach-completion-audit-2026-06-23.md": [
        "does not promote maturity labels",
        "production_ready: false",
        "stable_declaration: forbidden",
        "No production, stable, GA, or enterprise Beta promotion is claimed.",
    ],
    "docs/progress/alpha-magical-peach-pre-remote-ci-package-2026-06-23.md": [
        "does not close enterprise Beta or Production",
        "stable_declaration: forbidden",
        "level_3_sdk_platform: experimental",
        "production_ready: false",
    ],
    "docs/progress/external-gate-next-actions-2026-06-23.md": [
        "production_ready: false",
        "stable_declaration: forbidden",
        "level_3_sdk_platform: experimental",
        "not enterprise Beta",
    ],
    "docs/progress/adr-0016-0020-disposition-review-2026-06-23.md": [
        "production_ready: false",
        "must not be used as evidence for enterprise Beta, Production, GA",
    ],
    "production/sprints/sprint-017-external-validation-and-provider-hardening.md": [
        "production_ready",
        "stable_declaration",
    ],
}

PROMOTION_CLAIM_RE = re.compile(
    r"\b(production[- ]ready|enterprise[- ]ready|enterprise beta|stable|ga|beta)\b"
    r"|production_ready:\s*true"
    r"|stable_declaration:\s*(?!forbidden\b)\S+",
    re.IGNORECASE,
)

SAFE_CONTEXT_MARKERS = [
    "not",
    "no ",
    "does not",
    "do not",
    "must not",
    "cannot",
    "forbidden",
    "false",
    "experimental",
    "only after",
    "until",
    "before any",
    "without",
    "not sufficient",
    "not be used",
    "not be described",
    "not enterprise beta",
    "not close",
    "has not reached",
    "can be reconsidered only after",
    "no stable promotion authorized",
]

SAFE_NEARBY_CONTEXT_MARKERS = [
    "must not",
    "does not authorize",
    "not be used",
    "not be described",
    "not enterprise beta",
    "has not reached",
    "and not:",
]


def validate_texts(files: Mapping[str, str]) -> list[str]:
    errors: list[str] = []
    for file_id, snippets in REQUIRED_SNIPPETS.items():
        text = files.get(file_id)
        if text is None:
            errors.append(f"missing scanned alpha maturity file: {file_id}")
            continue
        for snippet in snippets:
            if snippet not in text:
                errors.append(f"{file_id}: missing required non-promotion snippet: {snippet}")

    for file_id, text in files.items():
        errors.extend(_scan_file(file_id, text))
    return errors


def _scan_file(file_id: str, text: str) -> list[str]:
    errors: list[str] = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        lower = line.lower()
        if re.search(r"\bproduction_ready:\s*true\b", lower):
            errors.append(
                f"{file_id}:{index + 1}: production_ready: true is forbidden in Alpha maturity evidence"
            )
            continue
        if re.search(r"\bstable_declaration:\s*(?!forbidden\b)\S+", lower):
            errors.append(
                f"{file_id}:{index + 1}: stable_declaration must remain forbidden in Alpha maturity evidence"
            )
            continue
        if not PROMOTION_CLAIM_RE.search(line):
            continue
        if _is_safe_claim_context(lines, index):
            continue
        errors.append(
            f"{file_id}:{index + 1}: possible unauthorized maturity promotion claim: {line.strip()}"
        )
    return errors


def _is_safe_claim_context(lines: list[str], index: int) -> bool:
    line = lines[index].lower()
    if lines[index].lstrip().lower().startswith("rg -n"):
        return True
    if _has_safe_line_marker(line):
        return True
    start = max(0, index - 5)
    end = min(len(lines), index + 3)
    context = " ".join(lines[start:end]).lower()
    return any(marker in context for marker in SAFE_NEARBY_CONTEXT_MARKERS)


def _has_safe_line_marker(line: str) -> bool:
    for marker in SAFE_CONTEXT_MARKERS:
        if marker == "not":
            if re.search(r"\bnot\b", line):
                return True
            continue
        if marker in line:
            return True
    return False


def _default_file_map(paths: list[Path]) -> dict[str, str]:
    files: dict[str, str] = {}
    for path in paths:
        file_id = _file_id(path)
        files[file_id] = path.read_text(encoding="utf-8")
    return files


def _file_id(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate that Alpha Magical Peach evidence keeps non-production maturity posture."
    )
    parser.add_argument(
        "--file",
        action="append",
        type=Path,
        dest="files",
        help="Optional file to scan. Defaults to the Alpha Magical Peach evidence file set.",
    )
    args = parser.parse_args(argv)

    paths = args.files if args.files else DEFAULT_FILES
    payload = _default_file_map(paths)
    errors = validate_texts(payload)
    result = {
        "passed": not errors,
        "errors": errors,
        "files": sorted(payload),
        "schema": "doge.alpha_maturity_honesty.v1",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

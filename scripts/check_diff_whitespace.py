from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def check_diff_whitespace(*, root: Path = ROOT) -> list[str]:
    completed = subprocess.run(
        ["git", "diff", "--no-color", "--unified=0"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode not in {0, 1}:
        return [completed.stderr.strip() or f"git diff exited {completed.returncode}"]

    errors: list[str] = []
    current_file: str | None = None
    new_line_no: int | None = None
    for raw_line in completed.stdout.splitlines(keepends=False):
        if raw_line.startswith("+++ b/"):
            current_file = raw_line.removeprefix("+++ b/")
            continue
        if raw_line.startswith("@@ "):
            new_line_no = _new_hunk_start(raw_line)
            continue
        if not raw_line.startswith("+") or raw_line.startswith("+++"):
            if raw_line.startswith(" ") and new_line_no is not None:
                new_line_no += 1
            continue

        content = raw_line[1:]
        content_without_cr = content[:-1] if content.endswith("\r") else content
        if content_without_cr.endswith((" ", "\t")):
            location = f"{current_file}:{new_line_no}" if current_file and new_line_no else current_file or "<unknown>"
            errors.append(f"{location}: trailing whitespace")
        if new_line_no is not None:
            new_line_no += 1
    return errors


def _new_hunk_start(line: str) -> int | None:
    marker = line.split(" ", 3)[2]
    if not marker.startswith("+"):
        return None
    raw_start = marker[1:].split(",", 1)[0]
    try:
        return int(raw_start)
    except ValueError:
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check changed lines for trailing whitespace while ignoring CRLF noise.")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)

    errors = check_diff_whitespace(root=args.root)
    print(json.dumps({"errors": errors, "passed": not errors}, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

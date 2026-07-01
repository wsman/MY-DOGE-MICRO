from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

try:
    from scripts.validate_alpha_maturity_honesty import validate_texts
except ModuleNotFoundError:
    from validate_alpha_maturity_honesty import validate_texts


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DOC_FILES = [
    ROOT / "README.md",
    ROOT / "docs" / "progress" / "current-status.md",
    ROOT / "docs" / "progress" / "runtime-maturity.yaml",
    ROOT / "docs" / "product" / "runtime-levels.md",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate public docs do not promote maturity claims."
    )
    parser.add_argument(
        "--file",
        action="append",
        type=Path,
        dest="files",
        help="Optional docs file to scan. Defaults to public maturity-facing docs.",
    )
    args = parser.parse_args(argv)

    paths = args.files if args.files else DEFAULT_DOC_FILES
    payload = _read_files(paths)
    errors = validate_texts(
        payload,
        require_alpha_file_set=False,
        require_posture_evidence=True,
    )
    result = {
        "errors": errors,
        "files": sorted(payload),
        "passed": not errors,
        "schema": "doge.docs_maturity_claims.v1",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not errors else 1


def _read_files(paths: list[Path]) -> dict[str, str]:
    payload: dict[str, str] = {}
    for path in paths:
        resolved = path if path.is_absolute() else ROOT / path
        payload[_file_id(resolved)] = resolved.read_text(encoding="utf-8")
    return payload


def _file_id(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())

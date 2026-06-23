from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_alpha_pending_payload import (
    REQUIRED_PENDING_PREFIXES,
    REQUIRED_PENDING_PATHS,
    validate as validate_pending_payload,
)


def analyze(status_lines: list[str], material_paths: set[str]) -> dict[str, Any]:
    errors = validate_pending_payload(status_lines)
    pending_paths = _pending_paths(status_lines)
    material_scope = analyze_material_scope(material_paths)
    errors.extend(material_scope["errors"])
    allowed_paths = set(REQUIRED_PENDING_PATHS)
    non_material_unexpected = sorted(
        path
        for path in pending_paths
        if not _is_allowed(path, allowed_paths=allowed_paths)
        and path not in material_paths
    )

    return {
        "passed": not errors,
        "errors": errors,
        "pending_paths": sorted(pending_paths),
        "material_paths": sorted(material_paths),
        "required_paths": REQUIRED_PENDING_PATHS,
        "required_prefixes": REQUIRED_PENDING_PREFIXES,
        "missing_material_required_paths": material_scope["missing_material_required_paths"],
        "missing_material_required_prefixes": material_scope["missing_material_required_prefixes"],
        "unexpected_material_paths": material_scope["unexpected_material_paths"],
        "non_material_unexpected_status_paths": non_material_unexpected,
    }


def analyze_material_scope(material_paths: set[str]) -> dict[str, Any]:
    errors: list[str] = []
    allowed_paths = set(REQUIRED_PENDING_PATHS)
    missing_material_required = sorted(
        path for path in REQUIRED_PENDING_PATHS if path not in material_paths
    )
    missing_material_required_prefixes = sorted(
        prefix
        for prefix in REQUIRED_PENDING_PREFIXES
        if not any(path.startswith(prefix) for path in material_paths)
    )
    unexpected_material = sorted(
        path
        for path in material_paths
        if not _is_allowed(path, allowed_paths=allowed_paths)
    )

    if unexpected_material:
        errors.append(
            "unexpected material paths in pending commit payload: "
            + ", ".join(unexpected_material)
        )
    for path in missing_material_required:
        errors.append(f"required material path missing from pending commit payload: {path}")
    for prefix in missing_material_required_prefixes:
        errors.append(f"required material directory missing from pending commit payload: {prefix}")

    return {
        "passed": not errors,
        "errors": errors,
        "material_paths": sorted(material_paths),
        "required_paths": REQUIRED_PENDING_PATHS,
        "required_prefixes": REQUIRED_PENDING_PREFIXES,
        "missing_material_required_paths": missing_material_required,
        "missing_material_required_prefixes": missing_material_required_prefixes,
        "unexpected_material_paths": unexpected_material,
    }


def _is_allowed(path: str, *, allowed_paths: set[str]) -> bool:
    if path in allowed_paths:
        return True
    return any(path.startswith(prefix) for prefix in REQUIRED_PENDING_PREFIXES)


def _pending_paths(status_lines: list[str]) -> set[str]:
    paths: set[str] = set()
    for line in status_lines:
        if len(line) < 4:
            continue
        path_text = line[3:]
        if " -> " in path_text:
            path_text = path_text.split(" -> ", 1)[1]
        paths.add(path_text.strip().strip('"').replace("\\", "/"))
    return paths


def _git_status_porcelain() -> list[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain=v1"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.splitlines()


def _git_material_paths() -> set[str]:
    diff = subprocess.run(
        ["git", "diff", "--name-only"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    paths = diff.stdout.splitlines() + staged.stdout.splitlines() + untracked.stdout.splitlines()
    return {path.strip().replace("\\", "/") for path in paths if path.strip()}


def git_commit_material_paths(commit_sha: str) -> set[str]:
    result = subprocess.run(
        ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_sha],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return {path.strip().replace("\\", "/") for path in result.stdout.splitlines() if path.strip()}


def git_commit_range_material_paths(base_sha: str, head_sha: str) -> set[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base_sha}..{head_sha}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return {path.strip().replace("\\", "/") for path in result.stdout.splitlines() if path.strip()}


def _read_path_set(path: Path) -> set[str]:
    return {
        line.strip().replace("\\", "/")
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate that the pending Alpha commit contains only the expected material payload."
    )
    parser.add_argument(
        "--status-file",
        type=Path,
        help="Optional file containing git status --porcelain=v1 output.",
    )
    parser.add_argument(
        "--material-paths-file",
        type=Path,
        help="Optional newline-delimited git diff/untracked path list.",
    )
    args = parser.parse_args(argv)

    status_lines = (
        args.status_file.read_text(encoding="utf-8").splitlines()
        if args.status_file
        else _git_status_porcelain()
    )
    material_paths = (
        _read_path_set(args.material_paths_file)
        if args.material_paths_file
        else _git_material_paths()
    )
    result = analyze(status_lines, material_paths)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

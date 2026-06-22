from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.export_plan_closure_manifest import DEFAULT_OUTPUT, build_manifest


def validate(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema") != "doge.plan_closure_execution_manifest.v1":
        errors.append("schema must be doge.plan_closure_execution_manifest.v1")
    generated_at = payload.get("generated_at")
    if not isinstance(generated_at, str) or not generated_at.strip():
        errors.append("generated_at is required")
        generated_at = "1970-01-01T00:00:00+00:00"
    else:
        try:
            datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        except ValueError:
            errors.append("generated_at must be ISO-8601")

    expected = build_manifest(generated_at=generated_at)
    if payload != expected:
        errors.append("manifest does not match current closure gate; rerun scripts/export_plan_closure_manifest.py")
        errors.extend(_manifest_differences(payload, expected))
    return errors


def _manifest_differences(payload: dict[str, Any], expected: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ["source_plan", "closure_gate", "operator_rule"]:
        if payload.get(key) != expected.get(key):
            errors.append(f"mismatch: {key}")
    payload_tasks = payload.get("tasks")
    expected_tasks = expected.get("tasks")
    if not isinstance(payload_tasks, list):
        errors.append("tasks must be a list")
        return errors
    if len(payload_tasks) != len(expected_tasks):
        errors.append(f"tasks length mismatch: expected {len(expected_tasks)}, got {len(payload_tasks)}")
    payload_by_id = {
        item.get("id"): item
        for item in payload_tasks
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    expected_by_id = {item["id"]: item for item in expected_tasks}
    missing = set(expected_by_id) - set(payload_by_id)
    extra = set(payload_by_id) - set(expected_by_id)
    if missing:
        errors.append(f"missing tasks: {', '.join(sorted(missing))}")
    if extra:
        errors.append(f"unexpected tasks: {', '.join(sorted(extra))}")
    for task_id in sorted(set(expected_by_id) & set(payload_by_id)):
        if payload_by_id[task_id] != expected_by_id[task_id]:
            errors.append(f"task mismatch: {task_id}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the 9b77f9c external closure execution manifest.")
    parser.add_argument("manifest", nargs="?", default=str(DEFAULT_OUTPUT), help="Manifest JSON path.")
    args = parser.parse_args(argv)

    path = Path(args.manifest)
    payload = json.loads(path.read_text(encoding="utf-8"))
    errors = validate(payload)
    result = {"path": str(path), "passed": not errors, "errors": errors}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

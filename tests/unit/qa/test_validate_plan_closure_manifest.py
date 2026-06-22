import json
from pathlib import Path
import subprocess
import sys

from scripts.export_plan_closure_manifest import DEFAULT_OUTPUT, build_manifest
from scripts.validate_plan_closure_manifest import validate


ROOT = Path(__file__).resolve().parents[3]


def test_plan_closure_manifest_matches_current_gate():
    payload = build_manifest(generated_at="2026-06-22T00:00:00+00:00")

    assert validate(payload) == []


def test_plan_closure_manifest_rejects_stale_task_list():
    payload = build_manifest(generated_at="2026-06-22T00:00:00+00:00")
    payload["tasks"] = payload["tasks"][:-1]

    errors = validate(payload)

    assert any("manifest does not match current closure gate" in error for error in errors)
    assert any("tasks length mismatch" in error for error in errors)
    assert any("missing tasks: S017-007" in error for error in errors)


def test_plan_closure_manifest_rejects_stale_source_plan_hash():
    payload = build_manifest(generated_at="2026-06-22T00:00:00+00:00")
    payload["source_plan_check"]["sha256"] = "0" * 64

    errors = validate(payload)

    assert any("manifest does not match current closure gate" in error for error in errors)
    assert any("mismatch: source_plan_check" in error for error in errors)


def test_plan_closure_manifest_cli_default_path():
    script = ROOT / "scripts" / "validate_plan_closure_manifest.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["path"] == str(DEFAULT_OUTPUT)
    assert payload["passed"] is True

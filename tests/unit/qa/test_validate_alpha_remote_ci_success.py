from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from scripts.validate_alpha_remote_ci_success import validate
from scripts.verify_remote_ci_evidence import SCHEMA


ROOT = Path(__file__).resolve().parents[3]
SHA = "e6398dab7975f130770608f411604d51ec300e43"
OTHER_SHA = "0" * 40


def test_alpha_remote_ci_success_accepts_exact_sha_wait_success():
    payload = _payload(wait_status="success")

    assert validate(payload, expected_head_sha=SHA) == []


def test_alpha_remote_ci_success_rejects_mismatched_expected_sha():
    payload = _payload(wait_status="success")

    errors = validate(payload, expected_head_sha=OTHER_SHA)

    assert any("must match expected target SHA" in error for error in errors)


def test_alpha_remote_ci_success_rejects_pending_remote_ci():
    payload = _payload(status="completed", conclusion="failure", result="pending_remote_ci", wait_status="terminal_failure")

    errors = validate(payload, expected_head_sha=SHA)

    assert "remote CI evidence result must be passed" in errors
    assert "remote CI evidence wait.status must be success" in errors
    assert any("no successful completed workflow run found" in error for error in errors)


def test_alpha_remote_ci_success_requires_wait_success_by_default():
    payload = _payload()

    errors = validate(payload, expected_head_sha=SHA)

    assert "remote CI evidence wait.status must be success" in errors
    assert validate(payload, expected_head_sha=SHA, require_wait_success=False) == []


def test_alpha_remote_ci_success_accepts_canonical_evidence_path():
    payload = _payload(wait_status="success")
    evidence_path = ROOT / "production" / "qa" / "evidence" / "ci" / "remote-ci-e6398da.json"

    errors = validate(
        payload,
        expected_head_sha=SHA,
        evidence_path=evidence_path,
        require_canonical_path=True,
    )

    assert errors == []


def test_alpha_remote_ci_success_rejects_noncanonical_evidence_path():
    payload = _payload(wait_status="success")

    errors = validate(
        payload,
        expected_head_sha=SHA,
        evidence_path="production/qa/evidence/ci/remote-ci-wrong.json",
        require_canonical_path=True,
    )

    assert (
        "remote CI evidence path must equal canonical target-SHA path: "
        "production/qa/evidence/ci/remote-ci-e6398da.json"
        in errors
    )


def test_alpha_remote_ci_success_rejects_temp_dir_canonical_suffix(tmp_path):
    payload = _payload(wait_status="success")
    evidence_path = tmp_path / "production" / "qa" / "evidence" / "ci" / "remote-ci-e6398da.json"

    errors = validate(
        payload,
        expected_head_sha=SHA,
        evidence_path=evidence_path,
        require_canonical_path=True,
    )

    assert any("must equal canonical target-SHA path" in error for error in errors)


def test_alpha_remote_ci_success_cli(tmp_path):
    evidence = tmp_path / "remote-ci.json"
    evidence.write_text(json.dumps(_payload(wait_status="success")), encoding="utf-8")
    script = ROOT / "scripts" / "validate_alpha_remote_ci_success.py"

    result = subprocess.run(
        [sys.executable, str(script), str(evidence), "--expected-head", SHA],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert '"passed": true' in result.stdout
    assert "https://github.com/wsman/MY-DOGE-MICRO/actions/runs/27967339069" in result.stdout


def test_alpha_remote_ci_success_cli_requires_canonical_path(tmp_path):
    evidence = tmp_path / "production" / "qa" / "evidence" / "ci" / "remote-ci-e6398da.json"
    evidence.parent.mkdir(parents=True)
    evidence.write_text(json.dumps(_payload(wait_status="success")), encoding="utf-8")
    script = ROOT / "scripts" / "validate_alpha_remote_ci_success.py"

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            str(evidence),
            "--expected-head",
            SHA,
            "--require-canonical-path",
            "--root",
            str(tmp_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert '"passed": true' in result.stdout


def _payload(
    *,
    status: str = "completed",
    conclusion: str | None = "success",
    result: str = "passed",
    wait_status: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema": SCHEMA,
        "generated_at": "2026-06-23T00:00:00Z",
        "repo": "wsman/MY-DOGE-MICRO",
        "head_sha": SHA,
        "required_workflow_name": "CI",
        "query_url": (
            "https://api.github.com/repos/wsman/MY-DOGE-MICRO/actions/runs"
            f"?head_sha={SHA}&per_page=20"
        ),
        "total_count": 1,
        "runs": [
            {
                "id": 27967339069,
                "name": "CI",
                "event": "push",
                "status": status,
                "conclusion": conclusion,
                "head_sha": SHA,
                "html_url": "https://github.com/wsman/MY-DOGE-MICRO/actions/runs/27967339069",
                "created_at": "2026-06-22T16:19:12Z",
                "updated_at": "2026-06-22T16:21:47Z",
            }
        ],
        "result": result,
    }
    if wait_status is not None:
        payload["wait"] = {
            "enabled": True,
            "attempts": 2,
            "status": wait_status,
            "timeout_seconds": 1800,
            "poll_interval_seconds": 15,
        }
    return payload

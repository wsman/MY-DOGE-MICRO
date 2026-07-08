from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from scripts.verify_remote_ci_evidence import (
    SCHEMA,
    _github_headers,
    build_evidence,
    validate,
    wait_for_evidence,
)


ROOT = Path(__file__).resolve().parents[3]
SHA = "e6398dab7975f130770608f411604d51ec300e43"


def test_validate_remote_ci_evidence_accepts_exact_sha_success():
    payload = _payload(_run(status="completed", conclusion="success"))

    assert validate(payload) == []


def test_validate_remote_ci_evidence_rejects_failed_run():
    payload = _payload(_run(status="completed", conclusion="failure"), result="passed")

    errors = validate(payload)

    assert any("no successful completed workflow run found for exact head SHA" in error for error in errors)
    assert "result must be pending_remote_ci" in errors


def test_validate_remote_ci_evidence_rejects_wrong_repo_and_query_url():
    payload = _payload(_run(status="completed", conclusion="success"))
    payload["repo"] = "attacker/not-target"
    payload["query_url"] = (
        "https://api.github.com/repos/attacker/not-target/actions/runs"
        f"?head_sha={SHA}&per_page=20"
    )

    errors = validate(payload)

    assert "repo must be wsman/MY-DOGE-MICRO" in errors
    assert "query_url path must be /repos/attacker/not-target/actions/runs" not in errors
    assert "query_url path must be /repos/wsman/MY-DOGE-MICRO/actions/runs" in errors


def test_validate_remote_ci_evidence_rejects_mismatched_query_head_sha():
    payload = _payload(_run(status="completed", conclusion="success"))
    payload["query_url"] = (
        "https://api.github.com/repos/wsman/MY-DOGE-MICRO/actions/runs"
        "?head_sha=0000000000000000000000000000000000000000&per_page=20"
    )

    errors = validate(payload)

    assert "query_url must include the exact head_sha query parameter" in errors


def test_validate_remote_ci_evidence_rejects_off_repo_success_run_url():
    payload = _payload(_run(status="completed", conclusion="success"))
    payload["runs"][0]["html_url"] = "https://example.invalid/wsman/MY-DOGE-MICRO/actions/runs/27967339069"

    errors = validate(payload)

    assert any("remote CI success run html_url must be" in error for error in errors)


def test_validate_remote_ci_evidence_accepts_transferred_repo_success_run_url():
    payload = _payload(_run(status="completed", conclusion="success"))
    payload["runs"][0]["html_url"] = "https://github.com/Negentropy-Laby/OpenDoge/actions/runs/27967339069"

    assert validate(payload) == []


def test_validate_remote_ci_evidence_rejects_unrelated_github_success_run_url():
    payload = _payload(_run(status="completed", conclusion="success"))
    payload["runs"][0]["html_url"] = "https://github.com/other/project/actions/runs/27967339069"

    errors = validate(payload)

    assert any("remote CI success run html_url must be one of:" in error for error in errors)


def test_validate_remote_ci_evidence_rejects_mismatched_sha():
    other_sha = "0" * 40
    payload = _payload(_run(head_sha=other_sha, status="completed", conclusion="success"))

    errors = validate(payload)

    assert any(f"no workflow run found for exact head_sha {SHA}" in error for error in errors)


def test_build_remote_ci_evidence_normalizes_github_runs(monkeypatch):
    response = {
        "total_count": 1,
        "workflow_runs": [
            {
                "id": 27967339069,
                "name": "CI",
                "event": "push",
                "status": "completed",
                "conclusion": "success",
                "head_sha": SHA,
                "html_url": "https://github.com/wsman/MY-DOGE-MICRO/actions/runs/27967339069",
                "created_at": "2026-06-22T16:19:12Z",
                "updated_at": "2026-06-22T16:21:47Z",
                "ignored": "not copied",
            }
        ],
    }
    monkeypatch.setattr(
        "scripts.verify_remote_ci_evidence._fetch_json",
        lambda url: response,
    )

    payload = build_evidence(owner="wsman", repo="MY-DOGE-MICRO", head_sha=SHA)

    assert payload["result"] == "passed"
    assert payload["query_url"].endswith(f"head_sha={SHA}&per_page=20")
    assert payload["runs"] == [
        {
            "id": 27967339069,
            "name": "CI",
            "event": "push",
            "status": "completed",
            "conclusion": "success",
            "head_sha": SHA,
            "html_url": "https://github.com/wsman/MY-DOGE-MICRO/actions/runs/27967339069",
            "created_at": "2026-06-22T16:19:12Z",
            "updated_at": "2026-06-22T16:21:47Z",
        }
    ]
    assert validate(payload) == []


def test_github_headers_use_env_token_without_exposing_it(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "  ghp_secret_token  ")
    monkeypatch.delenv("GH_TOKEN", raising=False)

    headers = _github_headers()

    assert headers["Authorization"] == "Bearer ghp_secret_token"
    assert "ghp_secret_token" not in json.dumps({"schema": SCHEMA})


def test_github_headers_ignore_blank_token(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "   ")
    monkeypatch.delenv("GH_TOKEN", raising=False)

    headers = _github_headers()

    assert "Authorization" not in headers


def test_wait_for_remote_ci_evidence_polls_until_success(monkeypatch):
    responses = [
        {"total_count": 1, "workflow_runs": [_github_run(status="queued", conclusion=None)]},
        {"total_count": 1, "workflow_runs": [_github_run(status="completed", conclusion="success")]},
    ]
    sleeps: list[float] = []
    now = [0.0]

    def fake_fetch(_url):
        return responses.pop(0)

    def fake_sleep(seconds):
        sleeps.append(seconds)
        now[0] += seconds

    monkeypatch.setattr("scripts.verify_remote_ci_evidence._fetch_json", fake_fetch)

    payload = wait_for_evidence(
        owner="wsman",
        repo="MY-DOGE-MICRO",
        head_sha=SHA,
        timeout_seconds=30,
        poll_interval_seconds=5,
        sleep=fake_sleep,
        clock=lambda: now[0],
    )

    assert payload["result"] == "passed"
    assert payload["wait"]["status"] == "success"
    assert payload["wait"]["attempts"] == 2
    assert sleeps == [5]
    assert validate(payload) == []


def test_wait_for_remote_ci_evidence_stops_on_terminal_failure(monkeypatch):
    calls = 0

    def fake_fetch(_url):
        nonlocal calls
        calls += 1
        return {"total_count": 1, "workflow_runs": [_github_run(status="completed", conclusion="failure")]}

    monkeypatch.setattr("scripts.verify_remote_ci_evidence._fetch_json", fake_fetch)

    payload = wait_for_evidence(
        owner="wsman",
        repo="MY-DOGE-MICRO",
        head_sha=SHA,
        timeout_seconds=30,
        poll_interval_seconds=5,
        sleep=lambda _seconds: None,
        clock=lambda: 0.0,
    )

    assert calls == 1
    assert payload["result"] == "pending_remote_ci"
    assert payload["wait"]["status"] == "terminal_failure"
    assert payload["wait"]["attempts"] == 1
    assert any("no successful completed workflow run found" in error for error in validate(payload))


def test_remote_ci_evidence_cli_validates_input(tmp_path):
    evidence = tmp_path / "remote-ci.json"
    evidence.write_text(json.dumps(_payload(_run(status="completed", conclusion="success"))), encoding="utf-8")
    script = ROOT / "scripts" / "verify_remote_ci_evidence.py"

    result = subprocess.run(
        [sys.executable, str(script), "--input", str(evidence)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert '"passed": true' in result.stdout


def _payload(run: dict[str, object], *, result: str | None = None) -> dict[str, object]:
    success = run.get("status") == "completed" and run.get("conclusion") == "success" and run.get("head_sha") == SHA
    return {
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
        "runs": [run],
        "result": result or ("passed" if success else "pending_remote_ci"),
    }


def _run(
    *,
    head_sha: str = SHA,
    status: str,
    conclusion: str | None,
) -> dict[str, object]:
    return {
        "id": 27967339069,
        "name": "CI",
        "event": "push",
        "status": status,
        "conclusion": conclusion,
        "head_sha": head_sha,
        "html_url": "https://github.com/wsman/MY-DOGE-MICRO/actions/runs/27967339069",
        "created_at": "2026-06-22T16:19:12Z",
        "updated_at": "2026-06-22T16:21:47Z",
    }


def _github_run(*, status: str, conclusion: str | None) -> dict[str, object]:
    run = _run(status=status, conclusion=conclusion)
    run["ignored"] = "not copied"
    return run

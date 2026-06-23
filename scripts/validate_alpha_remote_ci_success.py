from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.verify_remote_ci_evidence import validate as validate_remote_ci_evidence


def validate(
    payload: dict[str, Any],
    *,
    expected_head_sha: str | None = None,
    require_wait_success: bool = True,
    evidence_path: str | Path | None = None,
    require_canonical_path: bool = False,
    root: Path = ROOT,
) -> list[str]:
    errors = list(validate_remote_ci_evidence(payload))
    head_sha = payload.get("head_sha")
    workflow_name = payload.get("required_workflow_name")

    if expected_head_sha is not None:
        if not _is_sha(expected_head_sha):
            errors.append("expected_head_sha must be a 40-character lowercase hex commit SHA")
        elif head_sha != expected_head_sha:
            errors.append(
                "remote CI evidence head_sha must match expected target SHA: "
                f"expected {expected_head_sha}, found {head_sha!r}"
            )

    if payload.get("result") != "passed":
        errors.append("remote CI evidence result must be passed")

    if require_wait_success:
        wait = payload.get("wait")
        if not isinstance(wait, dict) or wait.get("status") != "success":
            errors.append("remote CI evidence wait.status must be success")

    if require_canonical_path:
        _validate_canonical_path(
            evidence_path=evidence_path,
            head_sha=head_sha,
            expected_head_sha=expected_head_sha,
            root=root,
            errors=errors,
        )

    success_runs = _success_runs(payload, head_sha=head_sha, workflow_name=workflow_name)
    if not success_runs:
        errors.append("remote CI evidence must include at least one exact-SHA completed/success run")
    elif not any(isinstance(run.get("html_url"), str) and run["html_url"] for run in success_runs):
        errors.append("remote CI success run must include html_url")

    return errors


def success_run_urls(payload: dict[str, Any]) -> list[str]:
    return [
        str(run["html_url"])
        for run in _success_runs(
            payload,
            head_sha=payload.get("head_sha"),
            workflow_name=payload.get("required_workflow_name"),
        )
        if isinstance(run.get("html_url"), str) and run["html_url"]
    ]


def _success_runs(
    payload: dict[str, Any],
    *,
    head_sha: Any,
    workflow_name: Any,
) -> list[dict[str, Any]]:
    if not isinstance(head_sha, str):
        return []
    workflow_filter = workflow_name if isinstance(workflow_name, str) else None
    runs = payload.get("runs")
    if not isinstance(runs, list):
        return []

    success: list[dict[str, Any]] = []
    for run in runs:
        if not isinstance(run, dict):
            continue
        if run.get("head_sha") != head_sha:
            continue
        if workflow_filter is not None and run.get("name") != workflow_filter:
            continue
        if run.get("status") == "completed" and run.get("conclusion") == "success":
            success.append(run)
    return success


def _validate_canonical_path(
    *,
    evidence_path: str | Path | None,
    head_sha: Any,
    expected_head_sha: str | None,
    root: Path,
    errors: list[str],
) -> None:
    if evidence_path is None:
        errors.append("remote CI evidence path is required when canonical path validation is enabled")
        return
    target_sha = expected_head_sha if expected_head_sha is not None else head_sha
    if not isinstance(target_sha, str) or not _is_sha(target_sha):
        errors.append("a valid target SHA is required for canonical path validation")
        return
    expected_rel = Path("production") / "qa" / "evidence" / "ci" / f"remote-ci-{target_sha[:7]}.json"
    expected_path = (root / expected_rel).resolve()
    try:
        actual_path = Path(evidence_path).resolve()
    except OSError as exc:
        errors.append(f"remote CI evidence path cannot be resolved: {exc}")
        return
    if actual_path != expected_path:
        errors.append(
            "remote CI evidence path must equal canonical target-SHA path: "
            f"{expected_rel.as_posix()}"
        )


def _is_sha(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{40}", value))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate that Alpha Magical Peach remote CI evidence closes for the exact target SHA."
    )
    parser.add_argument("evidence", type=Path, help="Remote CI evidence JSON from verify_remote_ci_evidence.py.")
    parser.add_argument("--expected-head", help="Exact target commit SHA that the evidence must match.")
    parser.add_argument(
        "--allow-no-wait-success",
        action="store_true",
        help="Do not require wait.status=success in the evidence payload.",
    )
    parser.add_argument(
        "--require-canonical-path",
        action="store_true",
        help="Require evidence path to equal production/qa/evidence/ci/remote-ci-<shortsha>.json under the repo root.",
    )
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root for canonical path validation.")
    args = parser.parse_args(argv)

    payload = json.loads(args.evidence.read_text(encoding="utf-8"))
    errors = validate(
        payload,
        expected_head_sha=args.expected_head,
        require_wait_success=not args.allow_no_wait_success,
        evidence_path=args.evidence,
        require_canonical_path=args.require_canonical_path,
        root=args.root,
    )
    result = {
        "path": str(args.evidence),
        "passed": not errors,
        "errors": errors,
        "expected_head": args.expected_head,
        "success_run_urls": success_run_urls(payload),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

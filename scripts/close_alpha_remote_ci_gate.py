from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.apply_alpha_remote_ci_success import (
    MATURITY,
    PLAN,
    apply_updates,
)
from scripts.validate_alpha_commit_scope import analyze_material_scope, git_commit_material_paths
from scripts.validate_alpha_final_closure import validate as validate_final_closure
from scripts.validate_alpha_remote_ci_success import validate as validate_remote_ci_success
from scripts.verify_remote_ci_evidence import DEFAULT_OWNER, DEFAULT_REPO, DEFAULT_WORKFLOW_NAME, wait_for_evidence


EvidenceFetcher = Callable[..., dict[str, Any]]
CommitScopeChecker = Callable[[str], list[str]]


def close_remote_ci_gate(
    *,
    head_sha: str | None = None,
    remote_ci_payload: dict[str, Any] | None = None,
    evidence_fetcher: EvidenceFetcher | None = None,
    output_dir: Path | str = ROOT / "production" / "qa" / "evidence" / "ci",
    plan_path: Path | str = PLAN,
    maturity_path: Path | str = MATURITY,
    owner: str = DEFAULT_OWNER,
    repo: str = DEFAULT_REPO,
    workflow_name: str | None = DEFAULT_WORKFLOW_NAME,
    timeout_seconds: float = 1800,
    poll_interval_seconds: float = 15,
    write: bool = False,
    gate_output: dict[str, Any] | None = None,
    root: Path = ROOT,
    require_commit_scope: bool | None = None,
    commit_scope_checker: CommitScopeChecker | None = None,
) -> dict[str, Any]:
    """Close the Alpha remote-CI DoD after exact-SHA CI success.

    The evidence JSON is always written to the canonical
    production/qa/evidence/ci/remote-ci-<shortsha>.json path. The source plan and
    runtime maturity files are only modified when `write` is true and all
    validation stages pass.
    """
    payload = remote_ci_payload
    target_sha = head_sha or _head_sha_from_payload(payload) or _git_head_sha()
    _validate_sha(target_sha)
    require_commit_scope = write if require_commit_scope is None else require_commit_scope

    if require_commit_scope:
        scope_errors = (
            commit_scope_checker(target_sha)
            if commit_scope_checker is not None
            else validate_commit_scope_for_sha(target_sha)
        )
        if scope_errors:
            return _result(
                passed=False,
                stage="post_commit_scope",
                head_sha=target_sha,
                evidence_path=Path(output_dir) / f"remote-ci-{target_sha[:7]}.json",
                errors=scope_errors,
                written=False,
            )

    evidence_path = Path(output_dir) / f"remote-ci-{target_sha[:7]}.json"
    canonical_errors = _validate_output_dir(output_dir=output_dir, target_sha=target_sha, root=root)
    if canonical_errors:
        return _result(
            passed=False,
            stage="canonical_output",
            head_sha=target_sha,
            evidence_path=evidence_path,
            errors=canonical_errors,
            written=False,
        )
    if payload is None:
        fetcher = evidence_fetcher or wait_for_evidence
        payload = fetcher(
            owner=owner,
            repo=repo,
            head_sha=target_sha,
            workflow_name=workflow_name,
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )

    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    success_errors = validate_remote_ci_success(
        payload,
        expected_head_sha=target_sha,
        evidence_path=evidence_path,
        require_canonical_path=True,
        root=root,
    )
    if success_errors:
        return _result(
            passed=False,
            stage="remote_ci_success",
            head_sha=target_sha,
            evidence_path=evidence_path,
            errors=success_errors,
            written=False,
        )

    plan_path = Path(plan_path)
    maturity_path = Path(maturity_path)
    apply_result = apply_updates(
        remote_ci_payload=payload,
        evidence_path=evidence_path,
        expected_head_sha=target_sha,
        plan_text=plan_path.read_text(encoding="utf-8"),
        maturity_text=maturity_path.read_text(encoding="utf-8"),
        root=root,
    )
    if not apply_result["passed"]:
        return _result(
            passed=False,
            stage="apply",
            head_sha=target_sha,
            evidence_path=evidence_path,
            errors=list(apply_result["errors"]),
            written=False,
        )

    final_errors = validate_final_closure(
        payload,
        evidence_path=evidence_path,
        expected_head_sha=target_sha,
        plan_text=apply_result["plan_text"],
        maturity_text=apply_result["maturity_text"],
        gate_output=gate_output,
        root=root,
    )
    if final_errors:
        return _result(
            passed=False,
            stage="final_closure",
            head_sha=target_sha,
            evidence_path=evidence_path,
            errors=final_errors,
            written=False,
        )

    if write:
        plan_path.write_text(apply_result["plan_text"], encoding="utf-8")
        maturity_path.write_text(apply_result["maturity_text"], encoding="utf-8")

    return _result(
        passed=True,
        stage="closed",
        head_sha=target_sha,
        evidence_path=evidence_path,
        errors=[],
        written=write,
        run_url=apply_result["run_url"],
        evidence_ref=apply_result["evidence_ref"],
    )


def _result(
    *,
    passed: bool,
    stage: str,
    head_sha: str,
    evidence_path: Path,
    errors: list[str],
    written: bool,
    run_url: str | None = None,
    evidence_ref: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "passed": passed,
        "stage": stage,
        "head_sha": head_sha,
        "short_sha": head_sha[:7],
        "remote_ci_evidence": str(evidence_path),
        "errors": errors,
        "written": written,
    }
    if run_url:
        result["run_url"] = run_url
    if evidence_ref:
        result["evidence_ref"] = evidence_ref
    return result


def _head_sha_from_payload(payload: dict[str, Any] | None) -> str | None:
    if isinstance(payload, dict) and isinstance(payload.get("head_sha"), str):
        return payload["head_sha"]
    return None


def _git_head_sha() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def validate_commit_scope_for_sha(head_sha: str) -> list[str]:
    material_paths = git_commit_material_paths(head_sha)
    return list(analyze_material_scope(material_paths)["errors"])


def _validate_output_dir(*, output_dir: Path | str, target_sha: str, root: Path) -> list[str]:
    expected = (root / "production" / "qa" / "evidence" / "ci" / f"remote-ci-{target_sha[:7]}.json").resolve()
    actual = (Path(output_dir) / f"remote-ci-{target_sha[:7]}.json").resolve()
    if actual != expected:
        return [
            "remote CI closure output must be the canonical repo path: "
            f"production/qa/evidence/ci/remote-ci-{target_sha[:7]}.json"
        ]
    return []


def _validate_sha(value: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise ValueError("head_sha must be a 40-character lowercase hex commit SHA")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the post-commit Alpha remote-CI closure sequence for the exact target SHA."
    )
    parser.add_argument("--head-sha", help="Exact post-commit target SHA. Defaults to evidence head_sha or git HEAD.")
    parser.add_argument(
        "--remote-ci-evidence",
        type=Path,
        help="Existing remote CI evidence JSON. If omitted, GitHub Actions evidence is fetched with wait polling.",
    )
    parser.add_argument("--output-dir", type=Path, default=ROOT / "production" / "qa" / "evidence" / "ci")
    parser.add_argument("--owner", default=DEFAULT_OWNER)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--workflow-name", default=DEFAULT_WORKFLOW_NAME)
    parser.add_argument("--timeout-seconds", type=float, default=1800)
    parser.add_argument("--poll-interval-seconds", type=float, default=15)
    parser.add_argument("--plan", type=Path, default=PLAN)
    parser.add_argument("--maturity", type=Path, default=MATURITY)
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root for canonical path validation.")
    parser.add_argument(
        "--skip-commit-scope",
        action="store_true",
        help="Skip target-SHA commit scope validation. Intended only for offline tests or emergency diagnostics.",
    )
    parser.add_argument("--write", action="store_true", help="Write plan/maturity updates after all checks pass.")
    args = parser.parse_args(argv)

    payload = None
    if args.remote_ci_evidence:
        payload = json.loads(args.remote_ci_evidence.read_text(encoding="utf-8"))

    result = close_remote_ci_gate(
        head_sha=args.head_sha,
        remote_ci_payload=payload,
        output_dir=args.output_dir,
        plan_path=args.plan,
        maturity_path=args.maturity,
        owner=args.owner,
        repo=args.repo,
        workflow_name=args.workflow_name or None,
        timeout_seconds=args.timeout_seconds,
        poll_interval_seconds=args.poll_interval_seconds,
        write=args.write,
        root=args.root,
        require_commit_scope=False if args.skip_commit_scope else None,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

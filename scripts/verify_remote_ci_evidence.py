from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen


SCHEMA = "doge.remote_ci_evidence.v1"
DEFAULT_OWNER = "wsman"
DEFAULT_REPO = "MY-DOGE-MICRO"
DEFAULT_WORKFLOW_NAME = "CI"
GITHUB_API_ROOT = "https://api.github.com"
GITHUB_WEB_ROOT = "https://github.com"
SUCCESS_RUN_REPO_ALIASES = {
    "wsman/MY-DOGE-MICRO": ("Negentropy-Laby/OpenDoge",),
}


def build_evidence(
    *,
    owner: str,
    repo: str,
    head_sha: str,
    workflow_name: str | None = DEFAULT_WORKFLOW_NAME,
    api_root: str = GITHUB_API_ROOT,
) -> dict[str, Any]:
    _validate_sha_shape(head_sha)
    query_url = _workflow_runs_url(api_root=api_root, owner=owner, repo=repo, head_sha=head_sha)
    payload = _fetch_json(query_url)
    runs = [
        _normalize_run(item)
        for item in payload.get("workflow_runs", [])
        if isinstance(item, dict)
    ]
    return {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "repo": f"{owner}/{repo}",
        "head_sha": head_sha,
        "required_workflow_name": workflow_name,
        "query_url": query_url,
        "total_count": payload.get("total_count"),
        "runs": runs,
        "result": "passed" if _success_run(runs, head_sha=head_sha, workflow_name=workflow_name) else "pending_remote_ci",
    }


def wait_for_evidence(
    *,
    owner: str,
    repo: str,
    head_sha: str,
    workflow_name: str | None = DEFAULT_WORKFLOW_NAME,
    api_root: str = GITHUB_API_ROOT,
    timeout_seconds: float = 600,
    poll_interval_seconds: float = 10,
    sleep: Any = time.sleep,
    clock: Any = time.monotonic,
) -> dict[str, Any]:
    if timeout_seconds < 0:
        raise ValueError("timeout_seconds must be non-negative")
    if poll_interval_seconds <= 0:
        raise ValueError("poll_interval_seconds must be positive")
    deadline = clock() + timeout_seconds
    attempts = 0
    last_evidence: dict[str, Any] | None = None
    wait_status = "timeout"

    while True:
        attempts += 1
        evidence = build_evidence(
            owner=owner,
            repo=repo,
            head_sha=head_sha,
            workflow_name=workflow_name,
            api_root=api_root,
        )
        last_evidence = evidence
        runs = evidence.get("runs", [])
        if evidence.get("result") == "passed":
            wait_status = "success"
            break
        if _terminal_non_success(runs, head_sha=head_sha, workflow_name=workflow_name):
            wait_status = "terminal_failure"
            break
        if clock() >= deadline:
            wait_status = "timeout"
            break
        sleep(min(poll_interval_seconds, max(0, deadline - clock())))

    assert last_evidence is not None
    last_evidence["wait"] = {
        "enabled": True,
        "attempts": attempts,
        "status": wait_status,
        "timeout_seconds": timeout_seconds,
        "poll_interval_seconds": poll_interval_seconds,
    }
    return last_evidence


def validate(
    payload: dict[str, Any],
    *,
    expected_repo: str = f"{DEFAULT_OWNER}/{DEFAULT_REPO}",
    api_root: str = GITHUB_API_ROOT,
    web_root: str = GITHUB_WEB_ROOT,
    success_run_repo_aliases: tuple[str, ...] | None = None,
) -> list[str]:
    errors: list[str] = []
    if payload.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA}")
    repo = payload.get("repo")
    if not isinstance(repo, str) or "/" not in repo:
        errors.append("repo must be owner/name")
        repo = ""
    elif repo != expected_repo:
        errors.append(f"repo must be {expected_repo}")
    head_sha = payload.get("head_sha")
    if not isinstance(head_sha, str) or not _is_sha(head_sha):
        errors.append("head_sha must be a 40-character lowercase hex commit SHA")
        head_sha = ""
    _validate_query_url(
        payload.get("query_url"),
        repo=expected_repo,
        head_sha=head_sha,
        api_root=api_root,
        errors=errors,
    )
    workflow_name = payload.get("required_workflow_name")
    if workflow_name is not None and not isinstance(workflow_name, str):
        errors.append("required_workflow_name must be a string or null")
        workflow_name = None
    runs = payload.get("runs")
    if not isinstance(runs, list):
        errors.append("runs must be a list")
        runs = []

    matching_runs: list[dict[str, Any]] = []
    for index, run in enumerate(runs):
        if not isinstance(run, dict):
            errors.append(f"runs[{index}] must be an object")
            continue
        run_errors = _validate_run(run, index=index)
        errors.extend(run_errors)
        if run.get("head_sha") == head_sha and (
            workflow_name is None or run.get("name") == workflow_name
        ):
            matching_runs.append(run)

    success = _success_run(runs, head_sha=head_sha, workflow_name=workflow_name)
    if not matching_runs:
        target = head_sha or "<invalid>"
        qualifier = f" and workflow {workflow_name!r}" if workflow_name else ""
        errors.append(f"no workflow run found for exact head_sha {target}{qualifier}")
    elif not success:
        states = ", ".join(
            f"{run.get('name')}#{run.get('id')}:{run.get('status')}/{run.get('conclusion')}"
            for run in matching_runs
        )
        errors.append(
            "no successful completed workflow run found for exact head SHA; "
            f"matching states: {states}"
        )

    expected_result = "passed" if success else "pending_remote_ci"
    if payload.get("result") != expected_result:
        errors.append(f"result must be {expected_result}")
    if success:
        _validate_success_run_urls(
            matching_runs,
            repos=_success_run_repos(
                expected_repo,
                aliases=success_run_repo_aliases,
            ),
            web_root=web_root,
            errors=errors,
        )
    return errors


def _workflow_runs_url(*, api_root: str, owner: str, repo: str, head_sha: str) -> str:
    root = api_root.rstrip("/")
    params = urlencode({"head_sha": head_sha, "per_page": "20"})
    return f"{root}/repos/{owner}/{repo}/actions/runs?{params}"


def _fetch_json(url: str) -> dict[str, Any]:
    request = Request(
        url,
        headers=_github_headers(),
    )
    try:
        with urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        raise RuntimeError(f"GitHub API request failed with HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"GitHub API request failed: {exc.reason}") from exc
    return json.loads(body)


def _github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "codex-remote-ci-evidence",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = _github_token_from_env()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _github_token_from_env() -> str | None:
    for name in ("GITHUB_TOKEN", "GH_TOKEN"):
        token = os.environ.get(name)
        if token and token.strip():
            return token.strip()
    return None


def _normalize_run(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "event": item.get("event"),
        "status": item.get("status"),
        "conclusion": item.get("conclusion"),
        "head_sha": item.get("head_sha"),
        "html_url": item.get("html_url"),
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
    }


def _validate_run(run: dict[str, Any], *, index: int) -> list[str]:
    errors: list[str] = []
    for key in ["id", "name", "status", "head_sha", "html_url"]:
        if run.get(key) in {None, ""}:
            errors.append(f"runs[{index}].{key} is required")
    if run.get("head_sha") not in {None, ""} and not _is_sha(str(run.get("head_sha"))):
        errors.append(f"runs[{index}].head_sha must be a 40-character lowercase hex commit SHA")
    if run.get("status") == "completed" and run.get("conclusion") in {None, ""}:
        errors.append(f"runs[{index}].conclusion is required when status is completed")
    return errors


def _validate_query_url(
    value: Any,
    *,
    repo: str,
    head_sha: str,
    api_root: str,
    errors: list[str],
) -> None:
    if not isinstance(value, str) or not value:
        errors.append("query_url is required")
        return
    parsed = urlparse(value)
    expected = urlparse(api_root.rstrip("/"))
    expected_path = f"/repos/{repo}/actions/runs"
    if parsed.scheme != expected.scheme or parsed.netloc != expected.netloc:
        errors.append(f"query_url must use {api_root.rstrip('/')}")
    if parsed.path != expected_path:
        errors.append(f"query_url path must be {expected_path}")
    query = parse_qs(parsed.query)
    if query.get("head_sha") != [head_sha]:
        errors.append("query_url must include the exact head_sha query parameter")


def _success_run_repos(
    repo: str,
    *,
    aliases: tuple[str, ...] | None,
) -> tuple[str, ...]:
    candidates = [repo]
    candidates.extend(aliases if aliases is not None else SUCCESS_RUN_REPO_ALIASES.get(repo, ()))
    repos: list[str] = []
    for candidate in candidates:
        if "/" not in candidate or candidate in repos:
            continue
        repos.append(candidate)
    return tuple(repos)


def _validate_success_run_urls(
    runs: list[dict[str, Any]],
    *,
    repos: tuple[str, ...],
    web_root: str,
    errors: list[str],
) -> None:
    expected = urlparse(web_root.rstrip("/"))
    for run in runs:
        if run.get("status") != "completed" or run.get("conclusion") != "success":
            continue
        html_url = run.get("html_url")
        if not isinstance(html_url, str) or not html_url:
            errors.append("remote CI success run must include html_url")
            continue
        parsed = urlparse(html_url)
        run_id = str(run.get("id"))
        expected_paths = tuple(f"/{repo}/actions/runs/{run_id}" for repo in repos)
        if parsed.scheme == expected.scheme and parsed.netloc == expected.netloc and parsed.path in expected_paths:
            continue
        expected_urls = ", ".join(f"{web_root.rstrip('/')}{path}" for path in expected_paths)
        errors.append(f"remote CI success run html_url must be one of: {expected_urls}")


def _success_run(
    runs: list[Any],
    *,
    head_sha: str,
    workflow_name: str | None,
) -> dict[str, Any] | None:
    for run in runs:
        if not isinstance(run, dict):
            continue
        if run.get("head_sha") != head_sha:
            continue
        if workflow_name is not None and run.get("name") != workflow_name:
            continue
        if run.get("status") == "completed" and run.get("conclusion") == "success":
            return run
    return None


def _terminal_non_success(
    runs: list[Any],
    *,
    head_sha: str,
    workflow_name: str | None,
) -> bool:
    matching: list[dict[str, Any]] = []
    for run in runs:
        if not isinstance(run, dict):
            continue
        if run.get("head_sha") != head_sha:
            continue
        if workflow_name is not None and run.get("name") != workflow_name:
            continue
        matching.append(run)
    if not matching:
        return False
    if any(run.get("status") != "completed" for run in matching):
        return False
    return all(run.get("conclusion") != "success" for run in matching)


def _validate_sha_shape(head_sha: str) -> None:
    if not _is_sha(head_sha):
        raise ValueError("head_sha must be a 40-character lowercase hex commit SHA")


def _is_sha(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{40}", value))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fetch or validate exact-SHA GitHub Actions evidence for the remote CI gate."
    )
    parser.add_argument("--input", type=Path, help="Existing remote CI evidence JSON to validate.")
    parser.add_argument("--output", type=Path, help="Where to write fetched evidence JSON.")
    parser.add_argument("--owner", default=DEFAULT_OWNER)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--head-sha", help="Exact 40-character commit SHA to query.")
    parser.add_argument("--workflow-name", default=DEFAULT_WORKFLOW_NAME, help="Workflow run name to require; use an empty string to accept any workflow.")
    parser.add_argument("--wait", action="store_true", help="Poll until exact-SHA CI success, terminal failure, or timeout.")
    parser.add_argument("--timeout-seconds", type=float, default=600, help="Maximum seconds to poll with --wait.")
    parser.add_argument("--poll-interval-seconds", type=float, default=10, help="Polling interval seconds with --wait.")
    args = parser.parse_args(argv)

    if args.input:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
    else:
        if not args.head_sha:
            parser.error("--head-sha is required when --input is not provided")
        workflow_name = args.workflow_name or None
        if args.wait:
            payload = wait_for_evidence(
                owner=args.owner,
                repo=args.repo,
                head_sha=args.head_sha,
                workflow_name=workflow_name,
                timeout_seconds=args.timeout_seconds,
                poll_interval_seconds=args.poll_interval_seconds,
            )
        else:
            payload = build_evidence(
                owner=args.owner,
                repo=args.repo,
                head_sha=args.head_sha,
                workflow_name=workflow_name,
            )
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    errors = validate(payload)
    result = {"passed": not errors, "errors": errors, "evidence": payload}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

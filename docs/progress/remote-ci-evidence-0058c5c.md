# Remote CI Evidence - 0058c5c

Date: 2026-06-23

## Verdict

Exact-SHA remote CI passed for baseline consolidation HEAD
`0058c5cd4ad5770fdbbcfd751d1bd3c95374d7c9`.

Canonical evidence:

```text
production/qa/evidence/ci/remote-ci-0058c5c.json
```

## GitHub Actions Run

| Field | Value |
|---|---|
| Repository | `wsman/MY-DOGE-MICRO` |
| Workflow | `CI` |
| Run ID | `28016915874` |
| Run URL | `https://github.com/wsman/MY-DOGE-MICRO/actions/runs/28016915874` |
| Event | `push` |
| Head SHA | `0058c5cd4ad5770fdbbcfd751d1bd3c95374d7c9` |
| Status | `completed` |
| Conclusion | `success` |

The CI workflow includes Python checks and TypeScript checks as defined in
`.github/workflows/ci.yml`.

## Evidence Commands

```powershell
$sha = git rev-parse HEAD
.\.venv\Scripts\python.exe scripts\verify_remote_ci_evidence.py --head-sha $sha --workflow-name CI --wait --timeout-seconds 60 --poll-interval-seconds 5 --output production\qa\evidence\ci\remote-ci-$($sha.Substring(0,7)).json
.\.venv\Scripts\python.exe scripts\validate_alpha_remote_ci_success.py production\qa\evidence\ci\remote-ci-$($sha.Substring(0,7)).json --expected-head $sha --require-canonical-path
```

Validation result:

```text
passed: true
success_run_urls:
  - https://github.com/wsman/MY-DOGE-MICRO/actions/runs/28016915874
```

## Scope Boundary

This evidence proves remote CI for `0058c5c` only. Any later commit created by
governance-closure work requires its own exact-SHA remote CI evidence before it
can be claimed as remotely verified.

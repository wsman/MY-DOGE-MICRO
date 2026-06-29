# Piped Donut Pre-Remote-CI Package - 2026-06-24

## Verdict

The local remediation package is ready for a future exact-SHA remote CI
attempt, but the plan is not complete.

This package records the local evidence and command path needed before
`C:\Users\Aby\.claude\plans\my-doge-micro-main-2ffdb66-piped-donut.md` can
close D-01.

## Current Boundary

- Source baseline HEAD: `2ffdb66e12865e00aba23808057eba87ca7aa116`
- Source baseline short HEAD: `2ffdb66`
- Current target status: `pending_remote_ci`
- Next target: post-commit SHA created after the A/B/C remediation payload is
  explicitly committed and pushed.

No commit or push has been performed by this package.

## Required Payload

The next remote-CI candidate commit must include these local closure artifacts.

| Area | Required files | Reason |
|---|---|---|
| Completion audit | `docs/progress/my-doge-micro-main-2ffdb66-piped-donut-completion-audit.md`, `scripts/validate_piped_donut_completion_audit.py`, `tests/unit/qa/test_validate_piped_donut_completion_audit.py` | Keeps A/B/C locally complete while preserving D-01/D-02/D-03 as open until exact-SHA CI and external evidence exist. |
| Pre-remote-CI package | `docs/archive/audits/piped-donut-pre-remote-ci-package-2026-06-24.md`, `scripts/validate_piped_donut_pre_remote_ci_package.py`, `tests/unit/qa/test_validate_piped_donut_pre_remote_ci_package.py` | Records the next exact-SHA remote CI handoff and machine-checks this package. |
| Remote CI gate | `scripts/verify_remote_ci_evidence.py`, `scripts/validate_alpha_remote_ci_success.py`, `tests/unit/qa/test_verify_remote_ci_evidence.py`, `tests/unit/qa/test_validate_alpha_remote_ci_success.py` | Provides exact head-SHA GitHub Actions fetch/validation and canonical `production/qa/evidence/ci/remote-ci-<shortsha>.json` success checks. The success validator is still Alpha-named, but its validation surface is generic and checks exact SHA, repo, GitHub run URL, wait status, and canonical evidence path. |
| SDK contract gate | `tools/ci/sdk-contract-check.py`, `tests/unit/ci/test_sdk_contract_check.py`, `.github/workflows/ci.yml` | Keeps OpenAPI, Python SDK, TypeScript SDK, Web client, and CI contract drift checks tied to the release-candidate SHA. |
| Migration and tenant closure | `migrations/`, `src/doge/infrastructure/database/migration_runner.py`, `src/doge/infrastructure/database/tenant_guard.py`, `tests/unit/infrastructure/test_migration_runner.py` | Keeps context-owned migrations and tenant guardrails in the release-candidate payload. |
| Runtime closure | `src/doge/infrastructure/database/sqlite_runtime_transaction.py`, `src/doge/infrastructure/database/event_subscriber.py`, `src/doge/application/agent/outbox_publisher.py`, `tests/contract/test_event_sequence_concurrency.py`, `tests/unit/agent/test_runtime_transaction.py`, `tests/unit/agent/test_event_subscriber.py`, `tests/unit/agent/test_worker_queue.py` | Preserves transaction, event, SSE, outbox, and worker-lease safety changes. |
| Code execution and module boundary closure | `src/doge/core/ports/code_executor.py`, `src/doge/infrastructure/code_execution/`, `src/doge/bootstrap/container.py`, `src/doge/bootstrap/runtime.py`, `src/doge/bootstrap/gateway.py`, `src/doge/bootstrap/workspace.py`, `src/doge/core/domain/run_execution_context.py`, `src/doge/core/domain/tool_descriptor.py`, `tests/unit/capabilities/test_code_executor.py`, `tests/unit/core/domain/test_run_execution_context.py` | Preserves default-off Python execution, split bootstrap, unified tool descriptor, and run execution context. |
| Shared external closure package | `docs/progress/9b77f9c-external-closure-runbook.md`, `production/qa/evidence/plan-closure/9b77f9c-external-closure-manifest.json`, `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/`, `scripts/validate_plan_closure_gate.py`, `scripts/preflight_plan_closure_external.py` | Preserves the shared S017 external gates: 6 total gates: 4 open / 2 passed. |

## Required Local Validation Before Commit

```powershell
.\.venv\Scripts\python.exe scripts\validate_piped_donut_completion_audit.py
.\.venv\Scripts\python.exe scripts\validate_piped_donut_pre_remote_ci_package.py
.\.venv\Scripts\python.exe tools\ci\sdk-contract-check.py
.\.venv\Scripts\python.exe scripts\validate_plan_closure_gate.py --allow-open
.\.venv\Scripts\python.exe scripts\preflight_plan_closure_external.py
.\.venv\Scripts\python.exe -m pytest -q
git diff --check
```

Expected current result before commit:

```text
local pytest = 1431 passed, 9 skipped, 11 warnings
plan closure gate = result open, 4 open / 2 passed
external preflight = infrastructure_ready true, result pending_external_inputs
remote CI = pending_remote_ci until a post-commit SHA exists
```

## Post-Commit Remote CI Step

After explicit user instruction to commit and push:

```powershell
$sha = git rev-parse HEAD
.\.venv\Scripts\python.exe scripts\verify_remote_ci_evidence.py --head-sha $sha --workflow-name CI --wait --timeout-seconds 1800 --poll-interval-seconds 15 --output production\qa\evidence\ci\remote-ci-$($sha.Substring(0,7)).json
.\.venv\Scripts\python.exe scripts\validate_alpha_remote_ci_success.py production\qa\evidence\ci\remote-ci-$($sha.Substring(0,7)).json --expected-head $sha --require-canonical-path
```

D-01 closes only when both commands exit `0` and the evidence records:

```text
status = completed
conclusion = success
head_sha = <exact post-commit SHA>
repo = wsman/MY-DOGE-MICRO
query_url = https://api.github.com/repos/wsman/MY-DOGE-MICRO/actions/runs?...head_sha=<exact post-commit SHA>
html_url = https://github.com/wsman/MY-DOGE-MICRO/actions/runs/<run_id>
wait.status = success
path = production/qa/evidence/ci/remote-ci-<shortsha>.json
```

## Non-Production Boundary

This package does not close D-02 or D-03. The external closure gate remains:

```text
6 total gates: 4 open / 2 passed
```

Still-open external gates:

- S017-003
- W3-live
- AUTH-prod
- S017-007

Passed external gates:

- S017-002
- S017-006

The required runtime posture remains:

```yaml
stable_declaration: forbidden
production_ready: false
```

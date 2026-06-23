# Alpha Magical Peach Pre-Remote-CI Package - 2026-06-23

## Verdict

The local repair package is ready for the next remote CI attempt, but the plan
is not complete.

This package records the commit payload that must move together into the next
target SHA before `C:\Users\Aby\.claude\plans\alpha-magical-peach.md` can close
its remote CI Definition of Done item.

## Current Boundary

- Current committed HEAD: `e6398dab7975f130770608f411604d51ec300e43`
- Current short HEAD: `e6398da`
- Current GitHub Actions run: `27967339069`
- Current run state: `CI#27967339069:completed/failure`
- Current remote CI result: `pending_remote_ci`
- Next target: post-commit SHA created from this local repair package

No commit or push has been performed by this package.

## Required Payload

The next commit for the remote CI attempt must include these critical files.

| Area | Required files | Reason |
|---|---|---|
| Completion audit | `docs/progress/alpha-magical-peach-completion-audit-2026-06-23.md`, `docs/progress/alpha-magical-peach-pre-remote-ci-package-2026-06-23.md`, `scripts/validate_alpha_magical_peach_completion_audit.py`, `scripts/validate_alpha_pre_remote_ci_package.py`, `scripts/validate_alpha_pending_payload.py`, `scripts/validate_alpha_maturity_honesty.py`, `scripts/validate_alpha_pre_commit_readiness.py`, `scripts/validate_alpha_commit_scope.py`, `scripts/apply_alpha_remote_ci_success.py`, `scripts/close_alpha_remote_ci_gate.py`, `scripts/validate_alpha_final_closure.py`, `tests/unit/qa/test_validate_alpha_magical_peach_completion_audit.py`, `tests/unit/qa/test_validate_alpha_pre_remote_ci_package.py`, `tests/unit/qa/test_validate_alpha_pending_payload.py`, `tests/unit/qa/test_validate_alpha_maturity_honesty.py`, `tests/unit/qa/test_validate_alpha_pre_commit_readiness.py`, `tests/unit/qa/test_validate_alpha_commit_scope.py`, `tests/unit/qa/test_apply_alpha_remote_ci_success.py`, `tests/unit/qa/test_close_alpha_remote_ci_gate.py`, `tests/unit/qa/test_validate_alpha_final_closure.py` | Keeps the plan locally hardened but not complete, with exact-SHA remote CI still pending, the pending commit scope bounded, maturity honesty machine-checked, one-command local pre-commit readiness available, and final closure proof executable after remote CI success. |
| Remote CI gate | `docs/progress/remote-ci-handoff-2026-06-23.md`, `scripts/verify_remote_ci_evidence.py`, `scripts/validate_alpha_remote_ci_success.py`, `scripts/close_alpha_remote_ci_gate.py`, `tests/unit/qa/test_verify_remote_ci_evidence.py`, `tests/unit/qa/test_validate_alpha_remote_ci_success.py`, `tests/unit/qa/test_close_alpha_remote_ci_gate.py` | Provides executable post-commit fetch, canonical evidence writing, success validation, plan/maturity update application, and final closure validation for GitHub Actions exact-SHA evidence. |
| External closure package | `production/qa/evidence/plan-closure/9b77f9c-external-closure-manifest.json`, `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/`, `scripts/validate_plan_closure_gate.py`, `scripts/export_plan_closure_manifest.py`, `scripts/prepare_plan_closure_handoff.py`, `scripts/validate_plan_closure_handoff.py`, `scripts/preflight_plan_closure_external.py`, `tests/unit/qa/test_export_plan_closure_manifest.py`, `tests/unit/qa/test_plan_closure_input_templates.py`, `tests/unit/qa/test_preflight_plan_closure_external.py`, `tests/unit/qa/test_prepare_plan_closure_handoff.py` | Preserves controlled-open external gate handling and operator handoff validation. |
| Governance planning | `docs/progress/adr-0016-0020-disposition-review-2026-06-23.md`, `docs/progress/external-gate-next-actions-2026-06-23.md`, `docs/progress/runtime-maturity.yaml`, `production/sprints/sprint-017-external-validation-and-provider-hardening.md`, `tests/unit/governance/test_s017_planning_docs.py` | Records ADR Proposed disposition, external-gate next actions, and non-production maturity posture. |
| Web SDK repair | `web/src/api/client.ts`, `web/src/api/portfolio.ts` | Keeps the Web build aligned with the local TypeScript SDK source imports used by the repaired validation baseline. |

## Required Local Validation Before Commit

```powershell
.\.venv\Scripts\python.exe scripts\validate_alpha_pre_remote_ci_package.py
.\.venv\Scripts\python.exe scripts\validate_alpha_pending_payload.py
.\.venv\Scripts\python.exe scripts\validate_alpha_maturity_honesty.py
.\.venv\Scripts\python.exe scripts\validate_alpha_pre_commit_readiness.py --mode fast
.\.venv\Scripts\python.exe scripts\validate_alpha_commit_scope.py
.\.venv\Scripts\python.exe scripts\validate_alpha_magical_peach_completion_audit.py
.\.venv\Scripts\python.exe -m py_compile scripts\verify_remote_ci_evidence.py scripts\validate_alpha_remote_ci_success.py scripts\validate_alpha_commit_scope.py scripts\validate_alpha_maturity_honesty.py scripts\validate_alpha_pre_commit_readiness.py scripts\apply_alpha_remote_ci_success.py scripts\close_alpha_remote_ci_gate.py scripts\validate_alpha_final_closure.py
.\.venv\Scripts\python.exe -m pytest tests\unit\qa\test_verify_remote_ci_evidence.py tests\unit\qa\test_validate_alpha_remote_ci_success.py tests\unit\qa\test_validate_alpha_commit_scope.py tests\unit\qa\test_validate_alpha_maturity_honesty.py tests\unit\qa\test_validate_alpha_pre_commit_readiness.py tests\unit\qa\test_apply_alpha_remote_ci_success.py tests\unit\qa\test_close_alpha_remote_ci_gate.py tests\unit\qa\test_validate_alpha_final_closure.py tests\unit\qa\test_validate_alpha_magical_peach_completion_audit.py tests\unit\qa\test_validate_alpha_pre_remote_ci_package.py tests\unit\qa\test_validate_alpha_pending_payload.py -q
.\.venv\Scripts\python.exe -m pytest tests\unit\governance\test_s017_planning_docs.py -q
.\.venv\Scripts\python.exe scripts\validate_plan_closure_gate.py --allow-open
.\.venv\Scripts\python.exe scripts\validate_plan_closure_manifest.py
.\.venv\Scripts\python.exe scripts\validate_plan_closure_handoff.py production\qa\evidence\plan-closure\handoffs\9b77f9c-2026-06-22
git diff --check
```

Expected current remote probe before commit:

```powershell
.\.venv\Scripts\python.exe scripts\verify_remote_ci_evidence.py --head-sha e6398dab7975f130770608f411604d51ec300e43 --workflow-name CI
```

Expected result:

```text
passed = false
result = pending_remote_ci
matching state = CI#27967339069:completed/failure
```

Current pending payload check:

```powershell
.\.venv\Scripts\python.exe scripts\validate_alpha_pending_payload.py
```

Expected result:

```text
passed = true
required pending paths and handoff directory prefix are present in git status
```

Current commit scope check:

```powershell
.\.venv\Scripts\python.exe scripts\validate_alpha_commit_scope.py
```

Expected result:

```text
passed = true
unexpected_material_paths = []
missing_material_required_paths = []
missing_material_required_prefixes = []
material paths include unstaged, staged, and untracked changes
status-only line-ending/index paths may be reported separately
```

## Post-Commit Closure Step

After explicit user instruction to commit/push:

```powershell
$sha = git rev-parse HEAD
.\.venv\Scripts\python.exe scripts\verify_remote_ci_evidence.py --head-sha $sha --workflow-name CI --wait --timeout-seconds 1800 --poll-interval-seconds 15 --output production\qa\evidence\ci\remote-ci-$($sha.Substring(0,7)).json
.\.venv\Scripts\python.exe scripts\validate_alpha_remote_ci_success.py production\qa\evidence\ci\remote-ci-$($sha.Substring(0,7)).json --expected-head $sha --require-canonical-path
```

Equivalent one-step closure helper:

```powershell
$sha = git rev-parse HEAD
.\.venv\Scripts\python.exe scripts\close_alpha_remote_ci_gate.py --head-sha $sha --write
```

The remote CI DoD closes only when both commands exit `0` and the evidence
records:

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

After the source plan and `docs/progress/runtime-maturity.yaml` are updated
with the new SHA, run URL, and evidence ref, final closure is proved by:

```powershell
.\.venv\Scripts\python.exe scripts\apply_alpha_remote_ci_success.py --remote-ci-evidence production\qa\evidence\ci\remote-ci-$($sha.Substring(0,7)).json --expected-head $sha --write
.\.venv\Scripts\python.exe scripts\validate_alpha_final_closure.py --remote-ci-evidence production\qa\evidence\ci\remote-ci-$($sha.Substring(0,7)).json --expected-head $sha
```

## Non-Production Boundary

This package does not close enterprise Beta or Production. The external closure
gate remains:

```text
6 total gates: 5 open / 1 passed
```

Still-open external gates:

- S017-002
- S017-003
- W3-live
- AUTH-prod
- S017-007

The required runtime posture remains:

```yaml
stable_declaration: forbidden
level_1: preview
level_2: alpha
level_3_sdk_platform: experimental
production_ready: false
```

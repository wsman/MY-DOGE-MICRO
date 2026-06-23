# Remote CI Handoff - 2026-06-23

## Verdict

The repaired working tree is locally CI-ready, but the remote CI gate is not
closed.

This handoff does not satisfy the `Remote CI success` Definition of Done item
in `C:\Users\Aby\.claude\plans\alpha-magical-peach.md`. It records the current
local evidence and the exact next steps needed to create a new target SHA and
obtain GitHub Actions evidence.

No commit or push has been performed because the project coordination rule says
there are no commits without explicit user instruction.

## Current Remote State

- Branch: `main`
- Local HEAD: `e6398dab7975f130770608f411604d51ec300e43`
- Local short HEAD: `e6398da`
- `origin/main`: `e6398da`
- GitHub Actions run for current committed HEAD:
  `https://github.com/wsman/MY-DOGE-MICRO/actions/runs/27967339069`
- Run event: `push`
- Run status: `completed`
- Run conclusion: `failure`
- Run created at: `2026-06-22T16:19:12Z`
- Run updated at: `2026-06-22T16:21:47Z`

The current repair changes are uncommitted, so they do not have a remote CI run
yet. The next remote CI target must be the post-commit SHA, not `e6398da`.

## Remote CI Evidence Verifier

The repo now includes `scripts/verify_remote_ci_evidence.py` to fetch and
validate exact-SHA GitHub Actions evidence. It queries workflow runs by
`head_sha`, preserves only non-secret run metadata, supports `--wait` polling
until success/terminal failure/timeout, and exits `0` only when the requested
workflow has a run with:

```text
status = completed
conclusion = success
head_sha = <exact target SHA>
repo = wsman/MY-DOGE-MICRO
query_url = GitHub Actions API URL for that repo and exact SHA
html_url = GitHub Actions run URL for that repo
```

The repo also includes `scripts/validate_alpha_remote_ci_success.py` as the
post-fetch closure validator. It accepts the evidence only when it is already
passed, its `head_sha` matches the expected target SHA, a success run URL is
present, and `wait.status = success` by default. The closure command also uses
`--require-canonical-path` so the resolved evidence path must equal the in-repo
canonical file `production/qa/evidence/ci/remote-ci-<shortsha>.json`.

The final post-success proof is handled by
`scripts/apply_alpha_remote_ci_success.py` plus
`scripts/validate_alpha_final_closure.py`, after the source plan and runtime
maturity record the new SHA, run URL, and canonical evidence ref.
`scripts/close_alpha_remote_ci_gate.py` wraps the full post-commit sequence:
validate the actual target SHA material scope, wait for exact-SHA CI, write
canonical evidence, validate success, apply the plan/maturity updates, and run
final closure validation.

Current probe against committed HEAD `e6398da` remains correctly open:

```powershell
.\.venv\Scripts\python.exe scripts\verify_remote_ci_evidence.py --head-sha e6398dab7975f130770608f411604d51ec300e43 --workflow-name CI
.\.venv\Scripts\python.exe scripts\verify_remote_ci_evidence.py --head-sha e6398dab7975f130770608f411604d51ec300e43 --workflow-name CI --wait --timeout-seconds 5 --poll-interval-seconds 1
```

Result:

```text
passed = false
result = pending_remote_ci
matching state = CI#27967339069:completed/failure
wait status = terminal_failure
exit code = 1
```

## Local Verification

Commands rerun for this handoff:

```powershell
.\.venv\Scripts\python.exe scripts\validate_governance_yaml_shape.py
.\.venv\Scripts\python.exe scripts\validate_kimi_plan_completion_audit.py
.\.venv\Scripts\python.exe scripts\validate_glowing_weaving_kettle_completion_audit.py
.\.venv\Scripts\python.exe scripts\validate_alpha_magical_peach_completion_audit.py
.\.venv\Scripts\python.exe scripts\validate_alpha_pre_remote_ci_package.py
.\.venv\Scripts\python.exe scripts\validate_alpha_pending_payload.py
.\.venv\Scripts\python.exe scripts\validate_alpha_commit_scope.py
.\.venv\Scripts\python.exe scripts\validate_plan_closure_gate.py --allow-open
.\.venv\Scripts\python.exe scripts\validate_plan_closure_manifest.py
.\.venv\Scripts\python.exe scripts\validate_plan_closure_runbook.py
.\.venv\Scripts\python.exe -m py_compile scripts\verify_remote_ci_evidence.py scripts\validate_alpha_remote_ci_success.py scripts\validate_alpha_commit_scope.py scripts\apply_alpha_remote_ci_success.py scripts\close_alpha_remote_ci_gate.py scripts\validate_alpha_final_closure.py
.\.venv\Scripts\python.exe -m pytest tests\unit\qa\test_verify_remote_ci_evidence.py -q
.\.venv\Scripts\python.exe -m pytest tests\unit\qa\test_validate_alpha_remote_ci_success.py -q
.\.venv\Scripts\python.exe -m pytest tests\unit\qa\test_validate_alpha_commit_scope.py -q
.\.venv\Scripts\python.exe -m pytest tests\unit\qa\test_apply_alpha_remote_ci_success.py -q
.\.venv\Scripts\python.exe -m pytest tests\unit\qa\test_close_alpha_remote_ci_gate.py -q
.\.venv\Scripts\python.exe -m pytest tests\unit\qa\test_validate_alpha_final_closure.py -q
.\.venv\Scripts\python.exe -m pytest tests\unit -q
.\.venv\Scripts\python.exe -m pytest tests\contract tests\integration -q
.\.venv\Scripts\python.exe -m pytest tests\eval -q
.\.venv\Scripts\python.exe -m pytest tests\unit\governance\test_adr_lifecycle_status.py -q
```

Results:

- Governance YAML shape: passed, 5 files, 0 findings.
- Kimi plan completion audit validator: passed.
- Glowing weaving kettle completion audit validator: passed.
- Alpha Magical Peach completion audit validator: passed.
- Alpha pre-remote-CI package validator: passed.
- Alpha pending payload validator: passed.
- Alpha commit scope validator: passed; unexpected material paths are empty,
  while status-only line-ending/index paths are reported separately.
- Plan closure gate with `--allow-open`: `result=open`, 5 open / 1 passed.
- Plan closure manifest validator: passed.
- Plan closure runbook validator: OK.
- Remote CI evidence verifier compile/unit tests: `10 passed`.
- Alpha remote CI success validator compile/unit tests: `9 passed`.
- Alpha commit scope validator compile/unit tests: `10 passed`.
- Alpha remote CI success applier compile/unit tests: `5 passed`.
- Alpha remote CI closure helper compile/unit tests: `7 passed`.
- Alpha final closure validator compile/unit tests: `6 passed`.
- Unit tests: `807 passed, 2 skipped, 8 warnings`.
- Contract + integration tests: `115 passed, 1 skipped`.
- Eval tests: `7 passed`.
- ADR lifecycle tests: `3 passed, 2 skipped`.

Node is not on the default PATH, so Web and TypeScript SDK checks used the
temporary Node runtime at:

```text
C:\Users\Aby\AppData\Local\Temp\codex-node-v24.17.0\node-v24.17.0-win-x64
```

Commands rerun with that path prepended:

```powershell
npm test
npm run build
```

Results:

- Web vitest: 13 files / 81 tests passed.
- Web build/typecheck: passed.
- TypeScript SDK vitest: 1 file / 13 tests passed.
- TypeScript SDK build: passed.

## Current Commit Scope

The repair/handoff working tree includes:

- Plan closure path normalization and handoff validation semantics.
- Web SDK source import fixes.
- Regenerated plan-closure manifest and handoff workspace.
- ADR-0016 through ADR-0020 disposition review evidence.
- External-gate next-action audit evidence.
- Remote CI handoff evidence.
- Governance tests covering ADR disposition, external next-action cards, this
  remote CI boundary, the bounded Alpha commit scope, the remote CI success
  applier, the one-step remote CI closure helper, and the final Alpha closure
  verifier.

The working tree also shows `web/tsconfig.app.json` and `web/vite.config.ts` as
modified in `git status` because of line-ending/index state, while
`git diff --name-only` does not report content diffs for those files.
`scripts/validate_alpha_commit_scope.py` reports that kind of status-only path
separately and fails only unexpected material paths.

## Remote CI Execution Steps

Only after explicit user instruction to commit:

1. Commit the current repair/handoff changes.
2. Record the new target SHA with:

   ```powershell
   git rev-parse HEAD
   git rev-parse --short HEAD
   ```

3. Push the commit, or open a branch/PR if the user chooses not to push to
   `main`.
4. Query and validate GitHub Actions for the new SHA:

   ```powershell
   $sha = git rev-parse HEAD
   .\.venv\Scripts\python.exe scripts\verify_remote_ci_evidence.py --head-sha $sha --workflow-name CI --wait --timeout-seconds 1800 --poll-interval-seconds 15 --output production\qa\evidence\ci\remote-ci-$($sha.Substring(0,7)).json
   .\.venv\Scripts\python.exe scripts\validate_alpha_remote_ci_success.py production\qa\evidence\ci\remote-ci-$($sha.Substring(0,7)).json --expected-head $sha --require-canonical-path
   ```

   Equivalent one-step closure helper:

   ```powershell
   .\.venv\Scripts\python.exe scripts\close_alpha_remote_ci_gate.py --head-sha $sha --scope-base-sha e6398dab7975f130770608f411604d51ec300e43 --write
   ```

5. The remote CI gate closes only when both commands exit `0` and the evidence
   records a run for the exact new SHA with:

   ```text
   status = completed
   conclusion = success
   wait.status = success
   path = production/qa/evidence/ci/remote-ci-<shortsha>.json
   ```

6. After success, update `C:\Users\Aby\.claude\plans\alpha-magical-peach.md`
   and `docs/progress/runtime-maturity.yaml` with the new SHA, run URL, and
   evidence ref:

   ```powershell
   .\.venv\Scripts\python.exe scripts\apply_alpha_remote_ci_success.py --remote-ci-evidence production\qa\evidence\ci\remote-ci-$($sha.Substring(0,7)).json --expected-head $sha --write
   ```

7. Prove final plan closure:

   ```powershell
   .\.venv\Scripts\python.exe scripts\validate_alpha_final_closure.py --remote-ci-evidence production\qa\evidence\ci\remote-ci-$($sha.Substring(0,7)).json --expected-head $sha
   ```

8. Rerun the governance/closure validators.

## Non-Production Boundary

Remote CI success is necessary for the plan's current Definition of Done, but
it is not sufficient for enterprise Beta or Production. The five external
evidence gates remain open until real passed/approved evidence exists:

- S017-002
- S017-003
- W3-live
- AUTH-prod
- S017-007

The required runtime posture remains:

```yaml
production_ready: false
stable_declaration: forbidden
level_3_sdk_platform: experimental
```

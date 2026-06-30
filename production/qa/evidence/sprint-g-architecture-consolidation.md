# Sprint G Architecture Consolidation Evidence

Date: 2026-06-30
Plan: `C:\Users\WSMAN\.claude\plans\according-to-a-document-fluttering-raven.md`
Sprint G closure SHA checked: `ee4c3283bb69ae21671ffd2d9fef908e4819ce16`

## Sprint G Closure CI

GitHub API returned one exact-SHA CI run for the Sprint G closure SHA:

- Run: `28448012096`
- Workflow: `CI`
- Event: `push`
- Status: `completed`
- Conclusion: `success`
- URL: `https://github.com/wsman/MY-DOGE-MICRO/actions/runs/28448012096`
- Evidence: `production/qa/evidence/ci/remote-ci-ee4c328.json`

Therefore Sprint G promotes
`latest_remotely_verified_sha.head_sha = ee4c3283bb69ae21671ffd2d9fef908e4819ce16`.

The prior pushed HEAD `9f304a82ae603f0d15210d7cbfc4e502a61fea43` had exact-SHA
CI run `28423757545` with conclusion `failure`; the failure was traced to stale
governance SHA-alignment assertions and fixed before this closure SHA.

## Focused Evidence Recorded Locally

- WP1/WP3/WP4/WP5 focused suite:
  `21 passed, 206 warnings`
- WP6 worker metrics focused suite:
  `13 passed, 2 warnings`
- WP7 streaming upload focused suite:
  `20 passed, 2 warnings`
- WP2 direct RuntimeKernel lifecycle focused suite:
  `42 passed, 73 warnings`

## Final Local Verification

- Architecture guard suite:
  `py -3 -m pytest tests\unit\architecture -q`
  result: `109 passed, 2 warnings`
- Eval suite:
  `py -3 -m pytest tests\eval\test_run_eval.py tests\eval\test_gold_eval.py tests\eval\test_failure_injection.py tests\eval\test_run_eval_metrics.py -q`
  result: `13 passed, 2 warnings`
- CLI / worker / upload suite:
  `py -3 -m pytest tests\cli\test_cli_batch.py tests\unit\agent\test_worker.py tests\unit\agent\test_worker_metrics.py tests\contract\test_v1_api.py::test_health_ready_reports_daemon_subsystems tests\unit\test_file_upload_service.py tests\unit\test_file_upload_large.py tests\contract\test_document_store.py tests\contract\test_document_large_upload.py -q`
  result: `34 passed, 2 warnings`
- CLI batch smoke:
  `py -3 -m doge.interfaces.cli.main batch --cases tests\eval\cases_expanded.json --output %TEMP%\doge-batch-sprint-g-results.json`
  result: `case_count=10`, `passed=10`
- Docs link validator:
  `py -3 scripts\validate_docs_links.py`
  result: `validated 62 markdown files`
- Maturity honesty validator:
  `py -3 scripts\validate_alpha_maturity_honesty.py`
  result: `passed`
- Plan closure gate:
  `py -3 scripts\validate_plan_closure_gate.py --allow-open`
  result: `acceptable open`, 4 open / 2 passed
- Strict plan closure gate:
  `py -3 scripts\validate_plan_closure_gate.py`
  result: `acceptable=false`, exit code 1 as expected while external gates remain open
- Whitespace check:
  `git diff --check`
  result: `passed`

## Remaining Gates

The following gates remain external/operator controlled and are not closed by
Sprint G:

- `S017-003`
- `W3-live`
- `AUTH-prod`
- `S017-007`

## Maturity Posture

- `production_ready: false`
- `stable_declaration: forbidden`
- `level_3_sdk_platform: experimental`

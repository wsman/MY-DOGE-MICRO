# Sprint G Architecture Consolidation Evidence

Date: 2026-06-30
Plan: `C:\Users\WSMAN\.claude\plans\according-to-a-document-fluttering-raven.md`
Current pushed HEAD checked: `9f304a82ae603f0d15210d7cbfc4e502a61fea43`

## Current-Head CI

GitHub API returned one exact-SHA CI run for current pushed HEAD:

- Run: `28423757545`
- Workflow: `CI`
- Event: `push`
- Status: `completed`
- Conclusion: `failure`
- URL: `https://github.com/wsman/MY-DOGE-MICRO/actions/runs/28423757545`

Therefore Sprint G must keep
`latest_remotely_verified_sha.head_sha = 6fd598ac223c390d81ea121d550d52afd3b47c87`
until a later exact-SHA CI run passes.

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

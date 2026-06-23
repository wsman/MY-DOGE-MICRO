# 9b77f9c External Closure Handoff Workspace

Prepared: 2026-06-23T01:13:51.821627+00:00
Date token: 2026-06-22
Source manifest: `production/qa/evidence/plan-closure/9b77f9c-external-closure-manifest.json`
Source plan SHA-256: `unavailable`
Operator command list: `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/operator-commands.ps1`

This workspace does not close any gate. It only copies operator input
templates into draft files and records the commands needed after real
external evidence is collected.

Do not place secrets, API keys, raw sensitive documents, or completed
evidence outputs in this workspace. Completed evidence must be written to
the output paths listed by each task and then validated with the strict
validator command.

## Tasks

### S017-002 - Live Kimi smoke execution

- Required result: `passed`
- Current status: `open` / `blocked`
- Handoff kind: `live_runner`
- Close condition: result must be passed; blocked evidence remains open
- Output ref: `production/qa/evidence/live/kimi-live-smoke-2026-06-22.json`
- Validator: `.\.venv\Scripts\python.exe scripts\validate_kimi_live_smoke_evidence.py production/qa/evidence/live/kimi-live-smoke-2026-06-22.json`
- Builder/runner: `.\.venv\Scripts\python.exe scripts\run_kimi_live_smoke.py --output-dir production/qa/evidence/live`
- Operator input guide: `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/s017-002/operator-input-guide.md`
- Prepared draft inputs: none; use the listed env/input refs.
- Input refs:
  - `env:DOGE_LIVE_KIMI=1`
  - `env:MOONSHOT_API_KEY`
  - `optional:env:DOGE_LIVE_KIMI_AGENT_SDK=1`
- Workspace command: `.\.venv\Scripts\python.exe scripts\run_kimi_live_smoke.py --output-dir production/qa/evidence/live`

Next action: Run scripts/run_kimi_live_smoke.py in an operator-approved Kimi credential/spend window with DOGE_LIVE_KIMI=1 and MOONSHOT_API_KEY set, then replace the blocked evidence with the live result.

### S017-003 - Financial provider fixture approval

- Required result: `approved`
- Current status: `open` / `not_run`
- Handoff kind: `evidence_builder`
- Close condition: result must be approved; needs_revision/rejected evidence remains open
- Output ref: `production/qa/evidence/provider/financial-provider-approval-YYYY-MM-DD.json`
- Validator: `.\.venv\Scripts\python.exe scripts\validate_financial_provider_approval_evidence.py production/qa/evidence/provider/financial-provider-approval-template-2026-06-22.json`
- Builder/runner: `.\.venv\Scripts\python.exe scripts\build_financial_provider_approval_evidence.py --decisions production/qa/evidence/provider/provider-decisions-YYYY-MM-DD.json --output production/qa/evidence/provider/financial-provider-approval-YYYY-MM-DD.json --created-at "YYYY-MM-DDTHH:MM:SSZ"`
- Operator input guide: `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/s017-003/operator-input-guide.md`
- Prepared draft inputs:
  - `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/s017-003/provider-decisions-draft-2026-06-22.json` from `production/qa/evidence/provider/provider-decisions-template-2026-06-22.json` (action: `preserved_existing_template_draft`, differs_from_source_template: `False`)
- Input refs:
  - `production/qa/evidence/provider/provider-decisions-YYYY-MM-DD.json`
- Draft input bindings:
  - `production/qa/evidence/provider/provider-decisions-YYYY-MM-DD.json` -> `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/s017-003/provider-decisions-draft-2026-06-22.json`
- Timestamp preamble: `$createdAt = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")`
- Operator placeholders: `$createdAt`
- Workspace command: `.\.venv\Scripts\python.exe scripts\build_financial_provider_approval_evidence.py --decisions production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/s017-003/provider-decisions-draft-2026-06-22.json --output production/qa/evidence/provider/financial-provider-approval-2026-06-22.json --created-at "$createdAt"`

Next action: Complete the provider approval template with product/operator decisions, license scope, fixture storage policy, freshness, provenance, and reviewer sign-off.

### W3-live - Analyst-labeled financial eval benchmark

- Required result: `passed`
- Current status: `open` / `not_run`
- Handoff kind: `evidence_builder`
- Close condition: result must be passed; failed evidence remains open
- Output ref: `production/qa/evidence/eval/analyst-benchmark-YYYY-MM-DD.json`
- Validator: `.\.venv\Scripts\python.exe scripts\validate_analyst_benchmark_evidence.py production/qa/evidence/eval/analyst-benchmark-template-2026-06-22.json`
- Builder/runner: `.\.venv\Scripts\python.exe scripts\build_analyst_benchmark_evidence.py --observations production/qa/evidence/eval/live-kimi-observations-redacted.json --thresholds production/qa/evidence/eval/approved-thresholds.json --output production/qa/evidence/eval/analyst-benchmark-YYYY-MM-DD.json --material-manifest-ref production/qa/evidence/eval/material-manifest-approved.json --label-manifest-ref production/qa/evidence/eval/label-manifest-approved.json --label-policy-ref docs/progress/financial-eval-gold-set.md --live-observation-ref production/qa/evidence/eval/live-kimi-observations-redacted.json --trend-history-ref production/qa/evidence/eval/trend-history.jsonl --analyst-role research-qa-analyst --analyst-initials "<initials>" --reviewed-at "YYYY-MM-DDTHH:MM:SSZ"`
- Operator input guide: `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/w3-live/operator-input-guide.md`
- Prepared draft inputs:
  - `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/w3-live/live-kimi-observations-draft-2026-06-22.json` from `production/qa/evidence/eval/live-kimi-observations-template-2026-06-22.json` (action: `preserved_existing_template_draft`, differs_from_source_template: `False`)
  - `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/w3-live/approved-thresholds-draft-2026-06-22.json` from `production/qa/evidence/eval/approved-thresholds-template-2026-06-22.json` (action: `preserved_existing_template_draft`, differs_from_source_template: `False`)
  - `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/w3-live/material-manifest-draft-2026-06-22.json` from `production/qa/evidence/eval/material-manifest-template-2026-06-22.json` (action: `preserved_existing_template_draft`, differs_from_source_template: `False`)
  - `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/w3-live/label-manifest-draft-2026-06-22.json` from `production/qa/evidence/eval/label-manifest-template-2026-06-22.json` (action: `preserved_existing_template_draft`, differs_from_source_template: `False`)
  - `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/w3-live/trend-history-draft-2026-06-22.jsonl` from `production/qa/evidence/eval/trend-history-template-2026-06-22.jsonl` (action: `preserved_existing_template_draft`, differs_from_source_template: `False`)
- Input refs:
  - `production/qa/evidence/eval/live-kimi-observations-redacted.json`
  - `production/qa/evidence/eval/approved-thresholds.json`
  - `production/qa/evidence/eval/material-manifest-approved.json`
  - `production/qa/evidence/eval/label-manifest-approved.json`
  - `production/qa/evidence/eval/trend-history.jsonl`
- Draft input bindings:
  - `production/qa/evidence/eval/live-kimi-observations-redacted.json` -> `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/w3-live/live-kimi-observations-draft-2026-06-22.json`
  - `production/qa/evidence/eval/approved-thresholds.json` -> `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/w3-live/approved-thresholds-draft-2026-06-22.json`
  - `production/qa/evidence/eval/material-manifest-approved.json` -> `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/w3-live/material-manifest-draft-2026-06-22.json`
  - `production/qa/evidence/eval/label-manifest-approved.json` -> `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/w3-live/label-manifest-draft-2026-06-22.json`
  - `production/qa/evidence/eval/trend-history.jsonl` -> `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/w3-live/trend-history-draft-2026-06-22.jsonl`
- Timestamp preamble: `$createdAt = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")`
- Operator placeholders: `$createdAt`, `<initials>`
- Workspace command: `.\.venv\Scripts\python.exe scripts\build_analyst_benchmark_evidence.py --observations production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/w3-live/live-kimi-observations-draft-2026-06-22.json --thresholds production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/w3-live/approved-thresholds-draft-2026-06-22.json --output production/qa/evidence/eval/analyst-benchmark-2026-06-22.json --material-manifest-ref production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/w3-live/material-manifest-draft-2026-06-22.json --label-manifest-ref production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/w3-live/label-manifest-draft-2026-06-22.json --label-policy-ref docs/progress/financial-eval-gold-set.md --live-observation-ref production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/w3-live/live-kimi-observations-draft-2026-06-22.json --trend-history-ref production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/w3-live/trend-history-draft-2026-06-22.jsonl --analyst-role research-qa-analyst --analyst-initials "<initials>" --reviewed-at "$createdAt"`

Next action: Fill the analyst benchmark evidence with real materials, human citation labels, live Kimi observations, thresholds, and trend-history metadata.

### AUTH-prod - Enterprise production validation

- Required result: `passed`
- Current status: `open` / `not_run`
- Handoff kind: `evidence_builder`
- Close condition: result must be passed; failed evidence remains open
- Output ref: `production/qa/evidence/enterprise/enterprise-production-validation-YYYY-MM-DD.json`
- Validator: `.\.venv\Scripts\python.exe scripts\validate_enterprise_production_validation_evidence.py production/qa/evidence/enterprise/enterprise-production-validation-template-2026-06-22.json`
- Builder/runner: `.\.venv\Scripts\python.exe scripts\build_enterprise_production_validation_evidence.py --observations production/qa/evidence/enterprise/enterprise-production-observations-YYYY-MM-DD.json --output production/qa/evidence/enterprise/enterprise-production-validation-YYYY-MM-DD.json --created-at "YYYY-MM-DDTHH:MM:SSZ"`
- Operator input guide: `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/auth-prod/operator-input-guide.md`
- Prepared draft inputs:
  - `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/auth-prod/enterprise-production-observations-draft-2026-06-22.json` from `production/qa/evidence/enterprise/enterprise-production-observations-template-2026-06-22.json` (action: `preserved_existing_template_draft`, differs_from_source_template: `False`)
- Input refs:
  - `production/qa/evidence/enterprise/enterprise-production-observations-YYYY-MM-DD.json`
- Draft input bindings:
  - `production/qa/evidence/enterprise/enterprise-production-observations-YYYY-MM-DD.json` -> `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/auth-prod/enterprise-production-observations-draft-2026-06-22.json`
- Timestamp preamble: `$createdAt = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")`
- Operator placeholders: `$createdAt`
- Workspace command: `.\.venv\Scripts\python.exe scripts\build_enterprise_production_validation_evidence.py --observations production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/auth-prod/enterprise-production-observations-draft-2026-06-22.json --output production/qa/evidence/enterprise/enterprise-production-validation-2026-06-22.json --created-at "$createdAt"`

Next action: Execute enterprise production validation against operator-approved IdP/JWKS, secret-store command, SIEM/WORM sink, remote deployment, and data-isolation review evidence.

### S017-006 - Research Agent screen-reader manual pass

- Required result: `passed`
- Current status: `passed` / `passed`
- Handoff kind: `evidence_builder`
- Close condition: result must be passed; failed evidence remains open
- Output ref: `production/qa/evidence/manual/research-agent-screen-reader-manual-YYYY-MM-DD.json`
- Validator: `.\.venv\Scripts\python.exe scripts\validate_screen_reader_evidence.py production/qa/evidence/manual/research-agent-screen-reader-manual-2026-06-22.json`
- Builder/runner: `.\.venv\Scripts\python.exe scripts\build_screen_reader_evidence.py --observations production/qa/evidence/manual/screen-reader-observations-YYYY-MM-DD.json --output production/qa/evidence/manual/research-agent-screen-reader-manual-YYYY-MM-DD.json --created-at "YYYY-MM-DDTHH:MM:SSZ"`
- Operator input guide: `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/s017-006/operator-input-guide.md`
- Prepared draft inputs:
  - `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/s017-006/screen-reader-observations-draft-2026-06-22.json` from `production/qa/evidence/manual/screen-reader-observations-template-2026-06-22.json` (action: `preserved_existing_operator_draft`, differs_from_source_template: `True`)
- Input refs:
  - `production/qa/evidence/manual/screen-reader-observations-YYYY-MM-DD.json`
- Draft input bindings:
  - `production/qa/evidence/manual/screen-reader-observations-YYYY-MM-DD.json` -> `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/s017-006/screen-reader-observations-draft-2026-06-22.json`
- Timestamp preamble: `$createdAt = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")`
- Operator placeholders: `$createdAt`
- Workspace command: `.\.venv\Scripts\python.exe scripts\build_screen_reader_evidence.py --observations production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/s017-006/screen-reader-observations-draft-2026-06-22.json --output production/qa/evidence/manual/research-agent-screen-reader-manual-2026-06-22.json --created-at "$createdAt"`

Next action: Run the S017 screen-reader manual protocol with an approved screen reader/browser combination and record pass/fail evidence.

### S017-007 - SDK registry publication approval

- Required result: `approved`
- Current status: `open` / `not_run`
- Handoff kind: `evidence_builder`
- Close condition: result must be approved; needs_revision/rejected evidence remains open
- Output ref: `production/qa/evidence/sdk/sdk-release-approval-YYYY-MM-DD.json`
- Validator: `.\.venv\Scripts\python.exe scripts\validate_sdk_release_approval_evidence.py production/qa/evidence/sdk/sdk-release-approval-template-2026-06-22.json`
- Builder/runner: `.\.venv\Scripts\python.exe scripts\build_sdk_release_approval_evidence.py --decisions production/qa/evidence/sdk/sdk-release-decisions-approved.json --output production/qa/evidence/sdk/sdk-release-approval-YYYY-MM-DD.json --created-at "YYYY-MM-DDTHH:MM:SSZ"`
- Operator input guide: `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/s017-007/operator-input-guide.md`
- Prepared draft inputs:
  - `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/s017-007/sdk-release-decisions-draft-2026-06-22.json` from `production/qa/evidence/sdk/sdk-release-decisions-template-2026-06-22.json` (action: `preserved_existing_template_draft`, differs_from_source_template: `False`)
- Input refs:
  - `production/qa/evidence/sdk/sdk-release-decisions-approved.json`
- Draft input bindings:
  - `production/qa/evidence/sdk/sdk-release-decisions-approved.json` -> `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/s017-007/sdk-release-decisions-draft-2026-06-22.json`
- Timestamp preamble: `$createdAt = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")`
- Operator placeholders: `$createdAt`
- Workspace command: `.\.venv\Scripts\python.exe scripts\build_sdk_release_approval_evidence.py --decisions production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/s017-007/sdk-release-decisions-draft-2026-06-22.json --output production/qa/evidence/sdk/sdk-release-approval-2026-06-22.json --created-at "$createdAt"`

Next action: Complete SDK release approval with registry targets, package-name ownership, version/changelog policy, registry-backed consumer smoke, and release-manager sign-off.

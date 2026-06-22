# Operator Input Guide - W3-live: Analyst-labeled financial eval benchmark

This guide does not close gates. It explains how to prepare real
operator inputs for one external closure gate.

Do not place secrets, API keys, raw sensitive documents, or completed
evidence outputs in this handoff workspace.

## Gate Contract

- Required result: `passed`
- Current status: `open` / `not_run`
- Close condition: result must be passed; failed evidence remains open
- Completed evidence belongs in: `production\qa\evidence\eval\analyst-benchmark-2026-06-22.json`
- Strict validator: `.\.venv\Scripts\python.exe scripts\validate_analyst_benchmark_evidence.py production\qa\evidence\eval\analyst-benchmark-2026-06-22.json`
- Builder/runner: `.\.venv\Scripts\python.exe scripts\build_analyst_benchmark_evidence.py --observations production\qa\evidence\eval\live-kimi-observations-redacted.json --thresholds production\qa\evidence\eval\approved-thresholds.json --output production\qa\evidence\eval\analyst-benchmark-YYYY-MM-DD.json --material-manifest-ref production/qa/evidence/eval/material-manifest-approved.json --label-manifest-ref production/qa/evidence/eval/label-manifest-approved.json --label-policy-ref docs/progress/financial-eval-gold-set.md --live-observation-ref production/qa/evidence/eval/live-kimi-observations-redacted.json --trend-history-ref production/qa/evidence/eval/trend-history.jsonl --analyst-role research-qa-analyst --analyst-initials "<initials>" --reviewed-at "YYYY-MM-DDTHH:MM:SSZ"`

## Fill Before Running

- Edit `production\qa\evidence\plan-closure\handoffs\9b77f9c-2026-06-22\inputs\w3-live\live-kimi-observations-draft-2026-06-22.json` prepared from `production\qa\evidence\eval\live-kimi-observations-template-2026-06-22.json` (action: `preserved_existing_template_draft`, differs_from_source_template: `False`).
- Edit `production\qa\evidence\plan-closure\handoffs\9b77f9c-2026-06-22\inputs\w3-live\approved-thresholds-draft-2026-06-22.json` prepared from `production\qa\evidence\eval\approved-thresholds-template-2026-06-22.json` (action: `preserved_existing_template_draft`, differs_from_source_template: `False`).
- Edit `production\qa\evidence\plan-closure\handoffs\9b77f9c-2026-06-22\inputs\w3-live\material-manifest-draft-2026-06-22.json` prepared from `production\qa\evidence\eval\material-manifest-template-2026-06-22.json` (action: `preserved_existing_template_draft`, differs_from_source_template: `False`).
- Edit `production\qa\evidence\plan-closure\handoffs\9b77f9c-2026-06-22\inputs\w3-live\label-manifest-draft-2026-06-22.json` prepared from `production\qa\evidence\eval\label-manifest-template-2026-06-22.json` (action: `preserved_existing_template_draft`, differs_from_source_template: `False`).
- Edit `production\qa\evidence\plan-closure\handoffs\9b77f9c-2026-06-22\inputs\w3-live\trend-history-draft-2026-06-22.jsonl` prepared from `production\qa\evidence\eval\trend-history-template-2026-06-22.jsonl` (action: `preserved_existing_template_draft`, differs_from_source_template: `False`).
- Required input ref: `production\qa\evidence\eval\live-kimi-observations-redacted.json`
- Required input ref: `production\qa\evidence\eval\approved-thresholds.json`
- Required input ref: `production\qa\evidence\eval\material-manifest-approved.json`
- Required input ref: `production\qa\evidence\eval\label-manifest-approved.json`
- Required input ref: `production\qa\evidence\eval\trend-history.jsonl`
- Replace operator value placeholders: `$createdAt`, `<initials>`

## Operator Focus

- Use real materials, human citation labels, approved thresholds, and live Kimi observations.
- Keep live observations redacted and reference the material, label, policy, and trend-history manifests.
- Replace <initials> with the approved analyst initials before running the builder.

## Run Order

1. From this workspace, run `powershell -ExecutionPolicy Bypass -File .\operator-commands.ps1 -TaskId W3-live`.
2. That command first runs `preflight_plan_closure_external.py --require-external-inputs`.
3. It then runs the builder/runner and the strict validator for this gate.
4. Run the final strict closure gate only after every external gate has completed evidence.

## Evidence Boundary

- Templates and copied drafts are not evidence.
- Completed evidence belongs in the production evidence path above, not inside this workspace.
- `needs_revision`, `rejected`, `failed`, `blocked`, and `not_run` do not close gates.
- Keep `production_ready: false` and `stable_declaration: forbidden` until a separate promotion review changes them.

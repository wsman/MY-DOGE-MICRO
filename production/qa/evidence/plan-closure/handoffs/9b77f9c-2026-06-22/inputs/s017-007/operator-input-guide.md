# Operator Input Guide - S017-007: SDK registry publication approval

This guide does not close gates. It explains how to prepare real
operator inputs for one external closure gate.

Do not place secrets, API keys, raw sensitive documents, or completed
evidence outputs in this handoff workspace.

## Gate Contract

- Required result: `approved`
- Current status: `open` / `not_run`
- Close condition: result must be approved; needs_revision/rejected evidence remains open
- Completed evidence belongs in: `production/qa/evidence/sdk/sdk-release-approval-2026-06-22.json`
- Strict validator: `.\.venv\Scripts\python.exe scripts\validate_sdk_release_approval_evidence.py production/qa/evidence/sdk/sdk-release-approval-2026-06-22.json`
- Builder/runner: `.\.venv\Scripts\python.exe scripts\build_sdk_release_approval_evidence.py --decisions production/qa/evidence/sdk/sdk-release-decisions-approved.json --output production/qa/evidence/sdk/sdk-release-approval-YYYY-MM-DD.json --created-at "YYYY-MM-DDTHH:MM:SSZ"`

## Fill Before Running

- Edit `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/s017-007/sdk-release-decisions-draft-2026-06-22.json` prepared from `production/qa/evidence/sdk/sdk-release-decisions-template-2026-06-22.json` (action: `preserved_existing_template_draft`, differs_from_source_template: `False`).
- Required input ref: `production/qa/evidence/sdk/sdk-release-decisions-approved.json`
- Replace operator value placeholders: `$createdAt`

## Operator Focus

- Record registry target, package-name ownership, version/changelog policy, and release-manager sign-off.
- Use a registry-backed consumer smoke result; local-only package checks do not approve release.
- Use needs_revision or rejected when registry, ownership, smoke, or sign-off evidence is incomplete.

## Run Order

1. From this workspace, run `powershell -ExecutionPolicy Bypass -File .\operator-commands.ps1 -TaskId S017-007`.
2. That command first runs `preflight_plan_closure_external.py --require-external-inputs`.
3. It then runs the builder/runner and the strict validator for this gate.
4. Run the final strict closure gate only after every external gate has completed evidence.

## Evidence Boundary

- Templates and copied drafts are not evidence.
- Completed evidence belongs in the production evidence path above, not inside this workspace.
- `needs_revision`, `rejected`, `failed`, `blocked`, and `not_run` do not close gates.
- Keep `production_ready: false` and `stable_declaration: forbidden` until a separate promotion review changes them.

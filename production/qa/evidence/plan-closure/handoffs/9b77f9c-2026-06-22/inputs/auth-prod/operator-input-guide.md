# Operator Input Guide - AUTH-prod: Enterprise production validation

This guide does not close gates. It explains how to prepare real
operator inputs for one external closure gate.

Do not place secrets, API keys, raw sensitive documents, or completed
evidence outputs in this handoff workspace.

## Gate Contract

- Required result: `passed`
- Current status: `open` / `not_run`
- Close condition: result must be passed; failed evidence remains open
- Completed evidence belongs in: `production/qa/evidence/enterprise/enterprise-production-validation-2026-06-22.json`
- Strict validator: `.\.venv\Scripts\python.exe scripts\validate_enterprise_production_validation_evidence.py production/qa/evidence/enterprise/enterprise-production-validation-2026-06-22.json`
- Builder/runner: `.\.venv\Scripts\python.exe scripts\build_enterprise_production_validation_evidence.py --observations production/qa/evidence/enterprise/enterprise-production-observations-YYYY-MM-DD.json --output production/qa/evidence/enterprise/enterprise-production-validation-YYYY-MM-DD.json --created-at "YYYY-MM-DDTHH:MM:SSZ"`

## Fill Before Running

- Edit `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/auth-prod/enterprise-production-observations-draft-2026-06-22.json` prepared from `production/qa/evidence/enterprise/enterprise-production-observations-template-2026-06-22.json` (action: `preserved_existing_template_draft`, differs_from_source_template: `False`).
- Required input ref: `production/qa/evidence/enterprise/enterprise-production-observations-YYYY-MM-DD.json`
- Replace operator value placeholders: `$createdAt`

## Operator Focus

- Validate against operator-approved IdP/JWKS, secret-store command, SIEM/WORM sink, and remote deployment evidence.
- Include data-isolation review evidence and keep redaction/security-review flags explicit.
- Use failed when any production dependency or isolation check is incomplete.

## Run Order

1. From this workspace, run `powershell -ExecutionPolicy Bypass -File .\operator-commands.ps1 -TaskId AUTH-prod`.
2. That command first runs `preflight_plan_closure_external.py --require-external-inputs`.
3. It then runs the builder/runner and the strict validator for this gate.
4. Run the final strict closure gate only after every external gate has completed evidence.

## Evidence Boundary

- Templates and copied drafts are not evidence.
- Completed evidence belongs in the production evidence path above, not inside this workspace.
- `needs_revision`, `rejected`, `failed`, `blocked`, and `not_run` do not close gates.
- Keep `production_ready: false` and `stable_declaration: forbidden` until a separate promotion review changes them.

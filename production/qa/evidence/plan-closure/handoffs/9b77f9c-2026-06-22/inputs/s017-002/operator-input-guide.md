# Operator Input Guide - S017-002: Live Kimi smoke execution

This guide does not close gates. It explains how to prepare real
operator inputs for one external closure gate.

Do not place secrets, API keys, raw sensitive documents, or completed
evidence outputs in this handoff workspace.

## Gate Contract

- Required result: `passed`
- Current status: `open` / `blocked`
- Close condition: result must be passed; blocked evidence remains open
- Completed evidence belongs in: `production/qa/evidence/live/kimi-live-smoke-2026-06-22.json`
- Strict validator: `.\.venv\Scripts\python.exe scripts\validate_kimi_live_smoke_evidence.py production/qa/evidence/live/kimi-live-smoke-2026-06-22.json`
- Builder/runner: `.\.venv\Scripts\python.exe scripts\run_kimi_live_smoke.py --output-dir production/qa/evidence/live`

## Fill Before Running

- No draft input file is copied for this gate; set the required refs below.
- Required input ref: `env:DOGE_LIVE_KIMI=1`
- Required input ref: `env:MOONSHOT_API_KEY`
- Required input ref: `optional:env:DOGE_LIVE_KIMI_AGENT_SDK=1`

## Operator Focus

- Confirm the operator-approved credential and spend window before running live Kimi.
- Set DOGE_LIVE_KIMI=1 and MOONSHOT_API_KEY in the environment only.
- Set DOGE_LIVE_KIMI_AGENT_SDK=1 only if the Agent SDK live path is approved for this run.
- Do not copy API keys, raw provider responses, or other secrets into the handoff workspace.

## Run Order

1. From this workspace, run `powershell -ExecutionPolicy Bypass -File .\operator-commands.ps1 -TaskId S017-002`.
2. That command first runs `preflight_plan_closure_external.py --require-external-inputs`.
3. It then runs the builder/runner and the strict validator for this gate.
4. Run the final strict closure gate only after every external gate has completed evidence.

## Evidence Boundary

- Templates and copied drafts are not evidence.
- Completed evidence belongs in the production evidence path above, not inside this workspace.
- `needs_revision`, `rejected`, `failed`, `blocked`, and `not_run` do not close gates.
- Keep `production_ready: false` and `stable_declaration: forbidden` until a separate promotion review changes them.

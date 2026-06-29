# 9b77f9c External Closure Operator Checklist

Workspace: `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22`
Command file: `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/operator-commands.ps1`
Source plan SHA-256: `unavailable`

This checklist does not close gates. It is a short execution index for
real operator evidence. Do not place secrets, API keys, raw sensitive
documents, or completed evidence outputs in the handoff workspace.

## Quick Start

1. Open the gate's `operator-input-guide.md` under `inputs/<gate-id>/`.
2. Fill only the draft inputs for the gate you are executing.
3. Run preflight for that gate through the generated command file.
4. Run the generated builder or live runner.
5. Run the strict validator for the produced evidence.
6. Run the final strict closure gate only after all six gates have real evidence.

Example single-gate command:

```powershell
powershell -ExecutionPolicy Bypass -File production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/operator-commands.ps1 -TaskId S017-003
```

Example final gate command after all evidence is complete:

```powershell
powershell -ExecutionPolicy Bypass -File production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/operator-commands.ps1 -RunFinalGate
```

## Task Checklist

| ID | Required result | Fill before running | Output evidence | Strict validator |
|----|----|----|----|----|
| S017-002 | passed | `env:DOGE_LIVE_KIMI=1`<br>`env:MOONSHOT_API_KEY`<br>`env:DOGE_LIVE_KIMI_AGENT_SDK=1`<br>`env:KIMI_FILES_API_CAPABLE=1`<br>`optional:env:DOGE_LIVE_KIMI_VISION_IMAGE` | `production/qa/evidence/live/kimi-live-smoke-2026-06-22.json` | `.\.venv\Scripts\python.exe scripts\validate_kimi_live_smoke_evidence.py --coding-v1 production/qa/evidence/live/kimi-live-smoke-2026-06-22.json` |
| S017-003 | approved | `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/s017-003/provider-decisions-draft-2026-06-22.json` | `production/qa/evidence/provider/financial-provider-approval-2026-06-22.json` | `.\.venv\Scripts\python.exe scripts\validate_financial_provider_approval_evidence.py production/qa/evidence/provider/financial-provider-approval-2026-06-22.json` |
| W3-live | passed | `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/w3-live/live-kimi-observations-draft-2026-06-22.json`<br>`production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/w3-live/approved-thresholds-draft-2026-06-22.json`<br>`production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/w3-live/material-manifest-draft-2026-06-22.json`<br>`production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/w3-live/label-manifest-draft-2026-06-22.json`<br>`production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/w3-live/trend-history-draft-2026-06-22.jsonl` | `production/qa/evidence/eval/analyst-benchmark-2026-06-22.json` | `.\.venv\Scripts\python.exe scripts\validate_analyst_benchmark_evidence.py production/qa/evidence/eval/analyst-benchmark-2026-06-22.json` |
| AUTH-prod | passed | `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/auth-prod/enterprise-production-observations-draft-2026-06-22.json` | `production/qa/evidence/enterprise/enterprise-production-validation-2026-06-22.json` | `.\.venv\Scripts\python.exe scripts\validate_enterprise_production_validation_evidence.py production/qa/evidence/enterprise/enterprise-production-validation-2026-06-22.json` |
| S017-006 | passed | `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/s017-006/screen-reader-observations-draft-2026-06-22.json` | `production/qa/evidence/manual/research-agent-screen-reader-manual-2026-06-22.json` | `.\.venv\Scripts\python.exe scripts\validate_screen_reader_evidence.py production/qa/evidence/manual/research-agent-screen-reader-manual-2026-06-22.json` |
| S017-007 | approved | `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/inputs/s017-007/sdk-release-decisions-draft-2026-06-22.json` | `production/qa/evidence/sdk/sdk-release-approval-2026-06-22.json` | `.\.venv\Scripts\python.exe scripts\validate_sdk_release_approval_evidence.py production/qa/evidence/sdk/sdk-release-approval-2026-06-22.json` |

## Guardrails

- Templates and copied drafts are not evidence.
- `needs_revision`, `rejected`, `failed`, `blocked`, and `not_run` do not close gates.
- Redaction and security-review flags must be explicit `false`; missing flags do not pass preflight or strict validation.
- Completed evidence belongs in the production evidence folders listed above, not inside this workspace.
- The final gate must keep `production_ready: false` and `stable_declaration: forbidden` until a separate promotion review changes them.

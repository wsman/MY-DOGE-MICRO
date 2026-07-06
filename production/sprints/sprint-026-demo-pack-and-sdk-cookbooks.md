# Sprint 026 - Demo Pack And SDK Cookbooks

Status: Local implementation complete / ready for local acceptance
Date: 2026-07-05

## Summary

Sprint 026 implements the interview/demo packet and standalone SDK cookbook
batch from `C:\Users\WSMAN\.claude\plans\agent-quizzical-wolf.md`.

## Scope

- Add ADR-0035 and this sprint CDD/governance trail.
- Add `DemoPackExporter`.
- Add `doge demo-pack --run-id/--case --output`.
- Export `run_summary.md`, `investment_memo.md`, `trace.jsonl`,
  `citations.json`, `metrics.json`, and `speaker_notes.md`.
- Add four Python SDK cookbook files.
- Add four TypeScript SDK cookbook files.
- Update CLI docs and SDK READMEs.
- Add focused use-case, CLI, cookbook, and CLI-doc-anchor tests.

## Explicitly Out of Scope

- Screenshots.
- Browser automation/headless rendering.
- New daemon API route.
- SDK public-resource or package-surface change.
- Research-case-to-run lookup.
- External/operator gate closure.

## Registration

This sprint is not registered in `production/sprint-status.yaml`. It follows
the UX/product-acceptance and governance-record sprint precedent where no new
story-status tracking is introduced.

## Verification Status

Local verification is recorded in
`production/qa/evidence/sprint-026-demo-pack-and-sdk-cookbooks-manifest.md`.

Initial focused result:

- Sprint 026 focused suite passed: 23 tests.
- TypeScript SDK build passed.
- SDK contract check passed at 13 surfaces / 13 parity.
- Governance validators passed; closure posture remained `4 open / 2 passed`.

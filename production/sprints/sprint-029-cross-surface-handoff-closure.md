# Sprint 029 - Cross-Surface Handoff Closure

Status: Local implementation complete / ready for local acceptance
Date: 2026-07-06

## Summary

Sprint 029 implements the cross-surface handoff plan from
`C:\Users\WSMAN\.claude\plans\a038a698-harmonic-mango.md`.

## Scope

- Add ADR-0038 and this sprint CDD/governance trail.
- Add `doge export` for local persisted memo export.
- Add human `doge run` next-action hints.
- Add `doged runs --status`, `doged explain`, and `doged support-bundle`.
- Add examples `.env`, README, Python Make targets, and TypeScript wrappers.
- Add Web evidence source-type tags.
- Add shared approval explanation component and use it in Research and Case
  approval panels.
- Add richer GuidedFlow states.
- Add FirstRunGuide for empty first Research workspace.
- Update CLI docs and focused tests.

## Explicitly Out of Scope

- `/v1` API surface changes.
- SDK package source changes.
- Persistence schema migration.
- Remote operator admin API.
- Production readiness declaration.

## Registration

This sprint is not registered in `production/sprint-status.yaml`. It follows
the UX/product-acceptance and governance-record sprint precedent where no new
story-status tracking is introduced.

## Verification Status

Local verification is recorded in
`production/qa/evidence/sprint-029-cross-surface-handoff-closure-manifest.md`.

Verification results:

- CLI/doged/example focused Python suite passed: 54 tests.
- Web focused suite passed: 21 tests.
- Full Web suite passed: 31 files, 143 tests.
- Web build passed.
- SDK contract passed: 15 surfaces, 15 entity parity checks.
- Docs authority, docs links, docs maturity claims, import boundaries,
  ADR/CDD maturity honesty, plan closure, and Windows Git whitespace checks
  passed.
- Plan closure posture remains controlled open: 4 open / 2 passed.

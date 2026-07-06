# Sprint 028 - Governance Progress

Status: Local implementation complete / ready for local acceptance
Date: 2026-07-05

## Summary

Sprint 028 implements the E4 governance workflow progress item from
`C:\Users\WSMAN\.claude\plans\agent-quizzical-wolf.md`.

## Scope

- Add ADR-0037 and this sprint CDD/governance trail.
- Add `CaseProgressStep` domain model.
- Add `case_progress_steps` persistence and migration support.
- Add platform repository save/list methods for case progress.
- Add derived progress from case, assets, executions, and decisions.
- Add `GET /v1/research-cases/{case_id}/progress`.
- Add Python SDK `platform.get_case_progress()`.
- Add TypeScript SDK `platform.getCaseProgress()` and `CaseProgressStep`.
- Add Web `getCaseProgress()` wrapper and platform store caching.
- Add `CaseProgressPanel.vue` to the case detail right rail.
- Update API route authority to 90 HTTP routes.
- Add focused repository, API, SDK, Web, and governance tests.

## Explicitly Out of Scope

- Editable workflow step state.
- SLA, notification, or escalation automation.
- External/operator gate closure.
- Production-ready maturity declaration.

## Registration

This sprint is not registered in `production/sprint-status.yaml`. It follows
the UX/product-acceptance and governance-record sprint precedent where no new
story-status tracking is introduced.

## Verification Status

Local verification is recorded in
`production/qa/evidence/sprint-028-governance-progress-manifest.md`.

Initial focused result:

- E4 repository/API/Python SDK tests passed: 3 tests.
- TypeScript SDK client spec passed: 17 tests.
- Web progress/store focused suite passed: 5 tests.
- SDK contract passed: 15 surfaces, 15 entity parity checks.
- API route coverage and governance route docs passed: 39 tests.

Final full governance verification is recorded in the evidence manifest.

# Sprint 027 - Run Comparison

Status: Local implementation complete / ready for local acceptance
Date: 2026-07-05

## Summary

Sprint 027 implements the B6 run comparison item from
`C:\Users\WSMAN\.claude\plans\agent-quizzical-wolf.md`.

## Scope

- Add ADR-0036 and this sprint CDD/governance trail.
- Add compact `GET /v1/runs`.
- Add `RunListItemResponse` / `RunListResponse`.
- Add Python SDK `runs.list()`.
- Add TypeScript SDK `runs.list()` and `RunListItem`.
- Add Web `listAgentRuns()` wrapper.
- Add `RunComparisonPanel.vue` to the Research Agent quality pane.
- Update API route authority to include the compact run-list route.
- Add focused API, SDK, Web, and governance tests.

## Explicitly Out of Scope

- Full memo diffing.
- New run status enum values.
- Persistence schema migration.
- Research-case timeline.
- External/operator gate closure.

## Registration

This sprint is not registered in `production/sprint-status.yaml`. It follows
the UX/product-acceptance and governance-record sprint precedent where no new
story-status tracking is introduced.

## Verification Status

Local verification is recorded in
`production/qa/evidence/sprint-027-run-comparison-manifest.md`.

Initial focused result:

- B6 Python route/SDK tests passed: 2 tests.
- TypeScript SDK client spec passed: 17 tests.
- Web comparison/view focused suite passed: 6 tests.
- Final governance and contract verification passed; details are in the
  manifest.

# Sprint UX-5 — Workspace Modes and Export

Status: Local implementation complete / ready for local acceptance
Date: 2026-07-05

## Summary

Sprint UX-5 implements B2 and B5 from
`C:\Users\WSMAN\.claude\plans\agent-quizzical-wolf.md`. UX-4 made the evidence
matrix usable; UX-5 cleans the default workspace into an analyst-first surface
and adds local memo export/copy actions for investment committee handoff.

## Scope

- Add ADR-0032 and this sprint CDD/governance trail.
- Add UI-only `analystMode` state to the agent store.
- Add ResearchAgentView Analyst/Developer mode controls.
- Hide raw diagnostics by default and reveal them only in Developer mode.
- Add browser-local Markdown and JSON memo export.
- Add Copy IC Questions and Copy citations.
- Keep PDF as browser print.
- Add focused Web tests for mode behavior, export helpers, export actions, and
  store state.

## Explicitly Out of Scope

- `/v1` export routes.
- SDK public-surface or parity-table changes.
- Persistence migrations.
- Server-side PDF/headless rendering.
- Runtime event, artifact, or citation authority changes.
- External/operator gate closure.

## Registration

This sprint is not registered in `production/sprint-status.yaml`. It follows
the UX-1 / UX-2 / Sprint 020-023 / UX-4 precedent for product-acceptance and
governance-record sprints that do not introduce new story-status tracking.

## Verification Status

Local verification is recorded in
`production/qa/evidence/sprint-ux-5-workspace-modes-and-export-manifest.md`.

Initial focused result:

- UX-5 Web focused suite passed: 3 files / 13 tests.
- Combined UX-4 + UX-5 Web focused suite passed: 6 files / 25 tests.
- Web build passed.
- SDK contract check passed at 13 surfaces / 13 parity.
- Governance validators passed; closure posture remained `4 open / 2 passed`.

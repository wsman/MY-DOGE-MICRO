# Sprint 030 - Analyst Product Home

Status: Local implementation complete / ready for local acceptance
Date: 2026-07-06

## Summary

Sprint 030 implements the Analyst Product Home plan from
`C:\Users\WSMAN\.claude\plans\a038a698-harmonic-mango.md`.

The sprint expands the existing `/home` platform shell view into an
analyst-first, mode-aware entry surface while preserving the existing operator
diagnostics in Developer mode.

## Scope

- Add ADR-0039 and this sprint CDD/governance trail.
- Expand `HomeDashboardView.vue` in place.
- Add Start Research and zero-key Run Demo actions.
- Embed recent run comparison on Home.
- Add recent uploads through `HomeRecentUploads.vue`.
- Render pending approvals, recent cases, recent memos, pending cases, and
  recent executions from existing platform store data.
- Add static portfolio import and demo-pack CTAs through
  `HomeStaticCtas.vue`.
- Render Local Alpha readiness through `MaturityPanel`.
- Gate failed/degraded and data freshness diagnostics behind Developer mode.
- Add focused Home and component tests.
- Update reader docs and active session state for Home.

## Explicitly Out of Scope

- `/v1` API surface changes.
- SDK package source changes.
- Persistence schema migration.
- Portfolio list endpoint.
- Demo-pack daemon endpoint.
- Product Home route rename or navigation registry change.
- Production readiness declaration.

## Registration

This sprint is not registered in `production/sprint-status.yaml`. It follows
the UX/product-acceptance and governance-record sprint precedent where no new
story-status tracking is introduced.

## Verification Status

Local verification is recorded in
`production/qa/evidence/sprint-030-analyst-product-home-manifest.md`.

Verification results:

- Focused Home Web suite passed: 5 files, 19 tests.
- Full Web suite passed: 34 files, 151 tests.
- Web build passed.
- SDK contract passed: 15 surfaces, 15 entity parity checks.
- Docs authority, docs links, docs maturity claims, import boundaries,
  ADR/CDD maturity honesty, plan closure, and Windows Git whitespace checks
  passed.
- Plan closure posture remains controlled open: 4 open / 2 passed.

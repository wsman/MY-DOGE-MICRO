# Sprint 025 - Portfolio Path Depth

Status: Local implementation complete / ready for local acceptance
Date: 2026-07-05

## Summary

Sprint 025 implements the E3 portfolio auto-summary batch from
`C:\Users\WSMAN\.claude\plans\agent-quizzical-wolf.md`. It turns CSV import
from a raw id-and-preview action into an immediate portfolio review surface.

## Scope

- Add ADR-0034 and this sprint CDD/governance trail.
- Add `PortfolioSummaryService`.
- Extend `POST /v1/portfolios/import` with an additive `summary` object.
- Preserve tenant-scoped portfolio import and summary lookup.
- Extend Web `ImportedPortfolio` summary types.
- Render holdings count, market value, top concentration, sector exposure,
  missing prices, and suggested run in `PortfolioImporter.vue`.
- Add focused service, API contract, enterprise tenant, and Web component tests.

## Explicitly Out of Scope

- New `/v1/portfolios/{id}/summary` route.
- SDK public-surface or parity-table changes.
- Persistence schema migration.
- Live price lookup.
- Portfolio CRUD.
- External/operator gate closure.

## Registration

This sprint is not registered in `production/sprint-status.yaml`. It follows
the UX/product-acceptance and governance-record sprint precedent where no new
story-status tracking is introduced.

## Verification Status

Local verification is recorded in
`production/qa/evidence/sprint-025-portfolio-path-depth-manifest.md`.

Initial focused result:

- Sprint 025 Python focused suite passed: 50 tests, 2 known FastAPI deprecation
  warnings.
- Sprint 025 Web component test passed: 1 test.
- Web build passed.
- SDK contract check passed at 13 surfaces / 13 parity.
- Governance validators passed; closure posture remained `4 open / 2 passed`.

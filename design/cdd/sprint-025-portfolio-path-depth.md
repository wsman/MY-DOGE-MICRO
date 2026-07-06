# Sprint 025 CDD: Portfolio Path Depth

Status: Ready for Acceptance
Date: 2026-07-05

## User Promise

After importing a portfolio CSV, an analyst immediately sees what matters:
holdings count, top concentration, sector exposure, unit-price gaps, and the
next agent run to launch.

## Delivered Contract

Sprint 025 implements the E3 portfolio auto-summary item from
`C:\Users\WSMAN\.claude\plans\agent-quizzical-wolf.md`:

- `PortfolioSummaryService` builds deterministic import summaries from the
  persisted portfolio.
- `POST /v1/portfolios/import` returns the previous portfolio payload plus an
  additive `summary` object.
- The same tenant scope used for import is used for summary lookup.
- `PortfolioImporter.vue` renders the summary below the CSV preview.
- The Web portfolio API type models the optional summary fields.

## Non-Goals

- No new standalone portfolio summary route.
- No SDK public-surface or SDK parity-table change.
- No persistence schema migration.
- No live price provider lookup.
- No portfolio CRUD surface.
- No external/operator gate closure.
- Current maturity posture remains `production_ready: false`,
  `stable_declaration: forbidden`, and Level 3 `experimental`.

## Acceptance Criteria

- Import summary includes holdings count.
- Import summary includes top-5 concentration rows sorted by market value.
- Import summary includes sector exposure rows.
- Import summary includes missing unit-price rows when quantity is absent or
  zero.
- Import summary includes the suggested `portfolio_risk_review` run question.
- Normal `/v1/portfolios/import` contract test asserts the summary.
- Enterprise portfolio import contract test asserts tenant-scoped summary
  behavior.
- Web component test asserts that the imported summary is rendered.
- Focused tests, Web build, SDK contract, docs validators, plan closure, and
  whitespace checks pass.

## Validation Plan

```bash
py -3 -m pytest tests/unit/test_portfolio_service.py tests/contract/test_v1_api.py tests/contract/test_enterprise_acl_api.py -q
cd web && npm run test -- src/components/agent/PortfolioImporter.spec.ts
cd web && npm run build
py -3 tools/ci/sdk-contract-check.py
py -3 scripts/validate_docs_authority.py
py -3 scripts/validate_alpha_maturity_honesty.py --file README.md
py -3 scripts/validate_docs_links.py
py -3 scripts/validate_import_boundaries.py
py -3 scripts/validate_docs_maturity_claims.py
py -3 scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0034-portfolio-import-auto-summary.md
py -3 scripts/validate_alpha_maturity_honesty.py --file design/cdd/sprint-025-portfolio-path-depth.md
py -3 scripts/validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/agent-quizzical-wolf.md
git diff --check
```

## Local Verification Result

- Initial focused Python suite passed: 50 tests, 2 known FastAPI deprecation
  warnings.
- Initial Web component suite passed: 1 test.
- Web build, SDK contract, docs authority, README/ADR/CDD maturity guards, docs
  links, import boundaries, docs maturity claims, plan closure, and whitespace
  checks passed.
- Full Sprint 025 verification is recorded in
  `production/qa/evidence/sprint-025-portfolio-path-depth-manifest.md`.

## Out of Scope

- Interview demo pack generation.
- SDK cookbook example files.
- Run comparison.
- Governance workflow progress visualization.
- External production/provider/operator gates.

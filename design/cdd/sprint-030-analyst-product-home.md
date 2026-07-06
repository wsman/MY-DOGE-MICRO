# Sprint 030 CDD: Analyst Product Home

Status: Ready for Acceptance
Date: 2026-07-06

## User Promise

A Web analyst can land on Home and immediately see where to start research,
which runs/uploads/cases need attention, which approvals and memos exist, and
whether the local Alpha runtime is ready enough to continue.

## Delivered Contract

Sprint 030 implements the Analyst Product Home plan in
`C:\Users\WSMAN\.claude\plans\a038a698-harmonic-mango.md`:

- `HomeDashboardView.vue` remains the `/home` route and `home-dashboard` view.
- Home adds a Start Research band with `Start research` and `Run demo`.
- `Run demo` uses the existing agent store, sets `earnings_review`, clears
  document and portfolio selection, and routes only after run state exists.
- Home renders recent runs through `RunComparisonPanel`.
- `HomeRecentUploads.vue` renders recent documents from the existing document
  list path.
- Home renders pending approvals, recent cases, recent memos, pending cases, and
  recent executions from existing platform store data.
- `HomeStaticCtas.vue` renders portfolio import and demo-pack entries without
  live list calls.
- Home renders Local Alpha readiness through `MaturityPanel`.
- Analyst mode hides operator diagnostics; Developer mode shows failed/degraded
  executions and data freshness warnings.
- Focused Home and component tests cover the new behavior.

## Non-Goals

- No `/v1` route, field, route-count, or response-model change.
- No SDK package source or public-surface change.
- No persistence migration or new runtime dependency.
- No portfolio list API.
- No demo-pack daemon API.
- No Product Home route rename or navigation registry change.
- No memo editor/versioning.
- No external/operator gate closure.
- Current maturity posture remains `production_ready: false`,
  `stable_declaration: forbidden`, and Level 3 `experimental`.

## Acceptance Criteria

- Home renders the analyst start band, recent runs, recent uploads, pending
  approvals, recent cases, recent memos, static workflow CTAs, pending cases,
  recent executions, and readiness.
- Home uses only existing data sources: `loadHomeQueue(20)`,
  `loadResearchCases({ limit: 10 })`, `documentStore.loadDocuments()`,
  `RunComparisonPanel`/`listAgentRuns(8)`, and `MaturityPanel`.
- `Start research` routes to `/research-agent`.
- `Run demo` calls the existing agent store with workflow `earnings_review`,
  empty document IDs, and null portfolio ID, then routes to `/research-agent`
  after the run is created.
- Analyst mode hides failed/degraded and data freshness diagnostics.
- Developer mode shows failed/degraded and data freshness diagnostics.
- `HomeRecentUploads` covers rendered, loading, empty, error, and upload-route
  states.
- `HomeStaticCtas` shows the in-memory portfolio ID when present and does not
  call nonexistent portfolio/demo-pack list APIs.
- Product navigation tests remain green: Home is not added to
  `PRIMARY_SCENARIO_NAV_ITEMS`, and the `home-dashboard` route remains intact.
- Docs and maturity validators keep Local Alpha posture honest.

## Validation Plan

```bash
cd web && npm run test -- --run src/views/HomeDashboardView.spec.ts src/components/home/HomeRecentUploads.spec.ts src/components/home/HomeStaticCtas.spec.ts src/router/productNavigation.spec.ts src/stores/platform.spec.ts
cd web && npm run test
cd web && npm run build
py -3 tools/ci/sdk-contract-check.py
py -3 scripts/validate_docs_authority.py
py -3 scripts/validate_docs_links.py
py -3 scripts/validate_docs_maturity_claims.py
py -3 scripts/validate_import_boundaries.py
py -3 scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0039-analyst-product-home.md
py -3 scripts/validate_alpha_maturity_honesty.py --file design/cdd/sprint-030-analyst-product-home.md
py -3 scripts/validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/a038a698-harmonic-mango.md
git diff --check
```

## Local Verification Result

Final local verification passed. Focused Home Web tests, full Web tests, Web
build, SDK contract parity, docs authority/links/maturity validators, import
boundaries, ADR/CDD honesty checks, plan closure, and whitespace checks all
passed. Evidence is recorded in
`production/qa/evidence/sprint-030-analyst-product-home-manifest.md`.

## Out of Scope

- SDK high-level `client.research.create_memo` helper.
- Python typed result model expansion.
- Web memo editor/version history.
- Operator TUI.
- Portfolio impact injection into generated memos.
- New API routes or production readiness work.

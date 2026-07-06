# Sprint 030 - Analyst Product Home Manifest

> Sprint: 030 (Analyst Product Home)
> Date: 2026-07-06
> Status: Local implementation complete; final verification passed.

## Scope

This manifest records local evidence for the Analyst Product Home expansion in
the Web platform shell.

## Implementation Evidence

| Area | Evidence |
|---|---|
| ADR | `docs/architecture/adr-0039-analyst-product-home.md` records the decision. |
| CDD | `design/cdd/sprint-030-analyst-product-home.md` records acceptance criteria. |
| Home view | `web/src/views/HomeDashboardView.vue` expands `/home` in place and preserves the `home-dashboard` route. |
| Recent uploads | `web/src/components/home/HomeRecentUploads.vue` lists documents through the existing document store. |
| Static CTAs | `web/src/components/home/HomeStaticCtas.vue` shows portfolio and demo-pack actions without list APIs. |
| Home tests | `web/src/views/HomeDashboardView.spec.ts`, `web/src/components/home/HomeRecentUploads.spec.ts`, and `web/src/components/home/HomeStaticCtas.spec.ts`. |
| Navigation guard | `web/src/router/productNavigation.spec.ts` confirms route/name/nav behavior remains unchanged. |
| Reader docs | `README.md` and `docs/start-here/research-workspace.md` describe Home as the analyst entry surface. |
| Session state | `production/session-state/active.md` records Sprint 030 as the current local implementation. |

## Verification Commands

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

## Verification Results

| Gate | Result |
|---|---|
| Focused Home Web suite | Passed: 5 files, 19 tests. |
| Full Web suite | Passed: 34 files, 151 tests. |
| Web build | Passed. |
| SDK contract | Passed: 15 surfaces, 15 entity parity checks. |
| Docs authority | Passed. |
| Docs links | Passed: 97 markdown files validated. |
| Docs maturity claims | Passed. |
| Import boundaries | Passed. |
| ADR/CDD maturity guard | Passed for ADR-0039 and Sprint 030 CDD. |
| Plan closure | Passed with controlled open posture: 4 open / 2 passed. |
| Whitespace | Passed with Windows Git `diff --check`. |

## Posture

- Production posture unchanged.
- No external/operator gates are closed by this sprint.
- No `/v1` route, SDK package source, persistence schema, or production
  readiness declaration is part of this sprint.

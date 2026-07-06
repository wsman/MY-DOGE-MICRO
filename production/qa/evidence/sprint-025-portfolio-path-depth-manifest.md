# Sprint 025 - Portfolio Path Depth Manifest

> Sprint: 025 (Portfolio Path Depth)
> Date: 2026-07-05
> Status: Local implementation complete; ready for local acceptance.

## Scope

This manifest records local evidence for the portfolio import auto-summary path.

## Implementation Evidence

| Area | Evidence |
|---|---|
| ADR | `docs/architecture/adr-0034-portfolio-import-auto-summary.md` records the decision to extend the existing import response rather than add a new route. |
| CDD | `design/cdd/sprint-025-portfolio-path-depth.md` records acceptance criteria. |
| Application service | `src/doge/application/services/portfolio_service.py` adds `PortfolioSummaryService`. |
| API dependencies | `src/doge/interfaces/api/deps.py` and `src/doge/interfaces/api/factories.py` wire the summary service. |
| Portfolio route | `src/doge/interfaces/gateway/routers/portfolios.py` adds additive `summary` to successful imports. |
| Web types | `web/src/api/portfolio.ts` models optional summary fields. |
| Web UI | `web/src/components/agent/PortfolioImporter.vue` renders the summary. |
| Python tests | `tests/unit/test_portfolio_service.py`, `tests/contract/test_v1_api.py`, and `tests/contract/test_enterprise_acl_api.py` cover service/API/tenant behavior. |
| Web tests | `web/src/components/agent/PortfolioImporter.spec.ts` covers summary rendering after upload. |

## Verification Commands

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

## Verification Results

| Gate | Result |
|---|---|
| Sprint 025 Python focused suite | Passed: 50 tests, 2 known FastAPI deprecation warnings. |
| Sprint 025 Web component suite | Passed: 1 test. |
| Web build | Passed. |
| SDK contract | Passed: 13 surfaces, 13 entity parity checks. |
| Docs authority | Passed. |
| README maturity guard | Passed. |
| ADR/CDD maturity guard | Passed for ADR-0034 and Sprint 025 CDD. |
| Docs links | Passed: 92 markdown files validated. |
| Import boundaries | Passed. |
| Docs maturity claims | Passed. |
| Plan closure | Passed with controlled-open posture: 4 open / 2 passed. |
| Whitespace | `git diff --check` passed. |

## Posture

- Production posture unchanged.
- No external/operator gates are closed by this sprint.
- No new route, SDK public-surface change, persistence migration, or live price
  provider dependency is part of this sprint.
- `summary` is an additive field on the existing portfolio import response.

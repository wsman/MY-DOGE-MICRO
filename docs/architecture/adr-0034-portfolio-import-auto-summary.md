# ADR-0034: Portfolio Import Auto Summary

## Status

Accepted

## Date

2026-07-05

## Decision Makers

wsman (product owner) · Codex implementation agent

## Summary

Sprint 025 implements the portfolio path-depth item from
`C:\Users\WSMAN\.claude\plans\agent-quizzical-wolf.md` by adding an automatic
summary to the existing portfolio CSV import path.

The key decision is to extend the existing `POST /v1/portfolios/import`
response with an additive `summary` object instead of adding a separate
portfolio-summary route. The summary is computed in the application service
layer and rendered by the Web `PortfolioImporter` panel.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python >=3.10; FastAPI 0.123.8; SQLite local agent DB; Vue 3 + Vite |
| **Domain** | Portfolio & Risk / Web workspace |
| **Knowledge Risk** | LOW - uses existing portfolio repository, CSV import route, tenant scope, and Vue component |
| **References Consulted** | `docs/reference/python/VERSION.md`, `standards/technical-preferences.md`, `docs/registry/architecture.yaml`, `design/cdd/bc-03-portfolio-risk.md`, `src/doge/application/services/portfolio_service.py`, `src/doge/interfaces/gateway/routers/portfolios.py`, `web/src/components/agent/PortfolioImporter.vue`, `C:\Users\WSMAN\.claude\plans\agent-quizzical-wolf.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | Focused portfolio service/API/Web tests, Web build, SDK contract check, docs/maturity validators, plan closure gate |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0021 (Bounded Context Consolidation), ADR-0024 (Single Stack Runtime Direction), ADR-0032 (Workspace Mode and Memo Export) |
| **Enables** | Sprint 025 portfolio path depth |
| **Blocks** | A standalone portfolio-management API until a future route contract ADR exists |
| **Ordering Note** | This ADR deepens the existing import path; it does not introduce portfolio CRUD, market-price refresh, or SDK resource expansion. |

## Context

### Problem Statement

The Web portfolio import panel accepts a CSV and returns an id, but it does not
turn the import into an immediately useful review surface. Analysts still need
to infer concentration, sector exposure, missing unit-price inputs, and the next
question to ask the agent.

### Constraints

- Preserve explicit maturity posture: `production_ready: false`,
  `stable_declaration: forbidden`, and Level 3 `experimental`.
- Keep the existing CSV import route and tenant-scope behavior.
- Do not add a new `/v1/portfolios/*` route, SDK method, SDK parity entry, or
  persistence schema migration.
- Do not fetch live prices or fabricate market data.
- Keep the Web panel useful when only market value is available.

### Requirements

- Imported portfolios return holdings count.
- Imported portfolios return top-5 concentration by market value.
- Imported portfolios return sector exposure.
- Imported portfolios return holdings where unit price cannot be derived.
- Imported portfolios return a suggested run prompt:
  `Analyze concentration and rate-shock risk for portfolio ...`.
- The Web import panel displays the summary next to the CSV preview.
- Enterprise tenant imports must summarize only the tenant-scoped portfolio just
  written.

## Decision

Add `PortfolioSummaryService` as an application-layer use case and call it from
the existing CSV import route after a successful import:

```text
POST /v1/portfolios/import
  -> PortfolioImportService.import_csv(...)
  -> PortfolioSummaryService.build_summary(portfolio_id, scope)
  -> existing portfolio response plus additive summary
```

The response remains a JSON object with the previous portfolio fields plus:

```json
{
  "summary": {
    "holdings_count": 2,
    "top_concentration": [],
    "by_sector": [],
    "missing_prices": [],
    "suggested_run": {
      "workflow": "portfolio_risk_review",
      "question": "Analyze concentration and rate-shock risk for portfolio portfolio-test."
    }
  }
}
```

### Key Interfaces

`PortfolioSummaryService.build_summary(portfolio_id, scope)` returns:

- `portfolio_id`
- `name`
- `total_market_value`
- `holdings_count`
- `top_concentration`
- `by_sector`
- `missing_prices`
- `suggested_run`

The Web `ImportedPortfolio` type gains optional `summary` fields because the
browser path consumes the additive route response directly.

## Alternatives Considered

### Alternative 1: Add `GET /v1/portfolios/{id}/summary`

- **Description**: Persist the portfolio, then fetch a second summary endpoint.
- **Pros**: Clean standalone read contract.
- **Cons**: Expands route inventory, API docs, authorization review, and SDK
  parity decisions.
- **Rejection Reason**: Sprint 025 needs import-path depth, not a new
  portfolio-management resource.

### Alternative 2: Compute summary only in Vue

- **Description**: Let `PortfolioImporter.vue` derive concentration and sector
  exposure from returned holdings.
- **Pros**: Fastest local implementation.
- **Cons**: Duplicates product logic in the Web layer and cannot be reused by
  CLI/API paths.
- **Rejection Reason**: Summary semantics belong in the application layer.

### Alternative 3: Fetch live prices during import

- **Description**: Resolve prices from market providers and compute missing
  price fields.
- **Pros**: Richer financial data.
- **Cons**: Requires provider credentials, external reliability handling, and
  operator evidence.
- **Rejection Reason**: Out of scope for local path-depth; imported market value
  remains the authority for this sprint.

## Consequences

### Positive

- Portfolio import now immediately surfaces concentration and exposure.
- The suggested run gives analysts a direct next step for value scenario 3.
- Existing route and tenant-scope behavior are preserved.

### Negative

- The import response is now a larger JSON object.
- Standalone portfolio summary retrieval remains deferred.
- Missing prices are inferred from absent quantity/unit-price derivability, not
  from a live pricing provider.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Response consumers assume exact keys only | LOW | LOW | Additive optional `summary`; previous fields unchanged. |
| Tenant-scoped imports summarize wrong repository state | LOW | MEDIUM | Summary service receives the same `TenantScope` used by import; enterprise contract test covers this. |
| Users mistake imported market value for live pricing | MEDIUM | LOW | `missing_prices` reports unit-price derivation gaps; no live-price claims are made. |

## CDD Requirements Addressed

| CDD Document | Requirement | How This ADR Addresses It |
|--------------|-------------|----------------------------|
| `design/cdd/bc-03-portfolio-risk.md` | Portfolio & Risk owns holdings, exposure, concentration, risk, and scenario analysis. | Adds import-time exposure and concentration summary. |
| `docs/architecture/module-boundaries.md` | Portfolio handles holdings, portfolio import, exposure, concentration, risk, scenario analysis. | Keeps summary in the Portfolio application service and product facade. |
| `design/cdd/product-concept.md` | Research and portfolio workflows should move users toward actionable agent runs. | Adds suggested portfolio risk review prompt after import. |

## Performance Implications

- **CPU**: O(n log n) over imported holdings for top concentration.
- **Memory**: Bounded by the existing imported holdings list.
- **Load Time**: One repository read after import.
- **Network**: No additional HTTP round trip; no external price provider call.

## Migration Plan

1. Add `PortfolioSummaryService`.
2. Export it through portfolio/application facades and API dependency factories.
3. Extend `POST /v1/portfolios/import` with additive `summary`.
4. Extend Web portfolio API types and `PortfolioImporter` display.
5. Add focused service, contract, enterprise, and Web component tests.
6. Record Sprint 025 CDD, sprint record, and evidence manifest.

## Validation Criteria

- Portfolio summary service returns holdings count, top concentration, sector
  exposure, missing-price rows, and suggested run.
- `/v1/portfolios/import` returns the additive summary for normal and enterprise
  tenant imports.
- Web portfolio import renders summary content after CSV upload.
- Existing portfolio import rejection behavior remains unchanged.
- Focused tests, Web build, and governance validators pass.

## Related Decisions

- ADR-0021: Bounded Context Consolidation
- ADR-0024: Single Stack Runtime Direction
- ADR-0032: Workspace Mode and Memo Export

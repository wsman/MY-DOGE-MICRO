# ADR-0001: Brownfield Clean Architecture Migration

## Status

Accepted

## Date

2026-06-11

## Last Verified

2026-06-11

## Decision Makers

WSMAN, Codex

## Summary

MY-DOGE-MICRO will migrate from legacy package/path coupling toward Clean Architecture with Ports & Adapters under `src/doge`. The migration is accepted as an incremental brownfield refactor: existing working entrypoints remain available while interfaces are routed through shared services and infrastructure adapters.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python 3.10+, FastAPI 0.123.8, MCP 1.25.0, PyQt6, SQLite, DuckDB 1.4.4, Vue 3/Vite 8 |
| **Domain** | Core architecture, data access, API/MCP/GUI interface boundaries |
| **Knowledge Risk** | MEDIUM - imported versions are from the source repository; latest upstream compatibility was not re-verified during metadata import |
| **References Consulted** | `docs/reference/python/VERSION.md`, `docs/imports/my-doge-micro/current-state-2026-06-11.md`, source `docs/MODULARIZATION_PLAN.md` |
| **Post-Cutoff APIs Used** | None specified by this ADR; implementation must verify any new FastAPI, MCP, Vue, or DuckDB APIs against local dependencies before shipping |
| **Verification Required** | Run pytest for Python/MCP/database flows and run the web build/type check before marking migration stories complete |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | None |
| **Enables** | Future ADRs for database repository contracts, API surface stabilization, MCP transport strategy, and web console architecture |
| **Blocks** | New cross-interface feature stories should not bypass service/port boundaries once their target service exists |
| **Ordering Note** | Keep compatibility entrypoints until CLI/API/MCP/GUI/Web paths are verified against the new services |

## Context

### Problem Statement

The source project has working market-analysis behavior, but important logic is spread across legacy modules, root scripts, direct database calls, and repeated project-root calculations. This makes testing, MCP/API reuse, and UI consistency harder as the product grows.

### Current State

The imported source state shows:

- Legacy tracked modules under `src/micro`, `src/macro`, and `src/interface`.
- Untracked new architecture under `src/doge/config`, `src/doge/core`, `src/doge/infrastructure`, and `src/doge/interfaces/mcp`.
- Untracked FastAPI routers under `src/api`.
- Untracked pytest coverage for database, MCP tools, and transport.
- Continued `sys.path.insert`, `_PROJECT_ROOT`, direct SQLite imports, and direct `connect_duckdb()` usage in legacy and interface modules.

### Constraints

- Existing user workflows must remain usable during migration.
- Local-first SQLite/DuckDB data must remain the source of truth for user data and reports.
- MCP, CLI, API, desktop UI, and web UI should converge on shared services rather than duplicate business rules.
- New design artifacts must reflect untracked source progress without copying source code into the CDD repository.

### Requirements

- Centralize runtime configuration and path handling.
- Move direct database access behind infrastructure adapters and repositories.
- Keep core services independent of interface frameworks.
- Route MCP/API/CLI/GUI/Web through shared service contracts when migrated.
- Preserve compatibility entrypoints until replacement paths are verified.

## Decision

Adopt Clean Architecture plus Ports & Adapters as the target structure for MY-DOGE-MICRO:

- `src/doge/config` owns runtime settings and path discovery.
- `src/doge/core/domain`, `core/ports`, and `core/services` own domain models, abstract contracts, and business services.
- `src/doge/infrastructure` implements database, cache, and market-data adapters.
- `src/doge/interfaces` owns MCP/API/CLI/GUI/Web integration surfaces.
- Legacy modules remain during migration but should stop receiving new architectural coupling.

### Architecture

```text
MCP / API / CLI / GUI / Web
        |
        v
Interfaces and dependency wiring
        |
        v
Core services
        |
        v
Core ports
        ^
        |
Infrastructure adapters
        |
        v
SQLite / DuckDB / TDX / yfinance / caches
```

### Key Interfaces

```text
Repository ports:
  StockRepository
  ReportRepository
  NoteRepository

Data source ports:
  MarketDataSource
  TickerMetadataSource

Core services:
  StockService
  RankingService
  BreadthService
  AnomalyService
  ViewService
```

Exact method signatures are owned by module CDDs and implementation stories. This ADR defines the layer boundary and migration direction.

### Implementation Guidelines

- Do not add new direct SQLite/DuckDB access in interface modules.
- Prefer dependency injection or narrow factory wiring at interface boundaries.
- Keep legacy root scripts as compatibility shims only when needed.
- Migrate one workflow at a time and verify it through tests before deleting legacy paths.
- Treat untracked `src/doge` files as active migration evidence that must be committed or otherwise preserved in the source repository before risky cleanup.

## Alternatives Considered

### Alternative 1: Keep Legacy Structure

- **Description**: Continue adding features directly to `src/micro`, `src/macro`, root MCP scripts, and API routers.
- **Pros**: Fastest short-term path; no migration overhead.
- **Cons**: Keeps direct DB/path coupling, duplicates behavior across interfaces, and makes tests brittle.
- **Estimated Effort**: Lowest initially, higher over time.
- **Rejection Reason**: It does not support reliable multi-interface growth.

### Alternative 2: Big-Bang Rewrite

- **Description**: Replace all legacy modules with `src/doge` structure at once.
- **Pros**: Clean target shape quickly.
- **Cons**: High breakage risk, difficult verification, and poor fit for a working local-first tool.
- **Estimated Effort**: Highest.
- **Rejection Reason**: Brownfield workflows need continuity and evidence-driven migration.

### Alternative 3: Interface-Only Refactor

- **Description**: Refactor MCP/API/Web/GUI entrypoints while leaving storage and services coupled.
- **Pros**: Improves outer surfaces.
- **Cons**: Does not solve duplicated business logic or direct storage access.
- **Estimated Effort**: Medium.
- **Rejection Reason**: The core maintainability problem is below the interface layer.

## Consequences

### Positive

- Shared services reduce behavior drift across MCP, API, CLI, GUI, and Web.
- Repository/data-source ports improve testability.
- Centralized configuration reduces path and environment bugs.
- Incremental migration preserves current working behavior.

### Negative

- Temporary duplication remains while legacy and new paths coexist.
- Developers must respect layer boundaries even before all code has migrated.
- More upfront design artifacts are needed before new implementation stories.

### Neutral

- The CDD workspace tracks governance metadata only; source changes still happen in `MY-DOGE-MICRO`.
- Some existing files may stay as compatibility shims after their responsibilities move.

> **Amendment (2026-06-12, S002-001 / TR-016 / OQ-11):** The RSRS zero-slope
> sign convention was unified to **zero → +1** across the two Python
> implementations on 2026-06-12: the scalar path (`src/micro/momentum_scanner.py:72`
> — `sign = 1.0 if float(slope) >= 0 else -1.0`) and the vectorized path
> (`src/micro/momentum_scanner.py:121` — `np.where(slope >= 0, 1.0, -1.0)`). The
> DuckDB-SQL views (`data/views.sql` `vw_rsrs_ranking_cn/us`) already use
> `CASE WHEN ... >= 0 THEN 1`, so the zero-boundary sign helper matches at the
> helper level. NOTE: the zero-boundary convention is moot for the RSRS *product*
> value, because a zero-slope series necessarily has R² = 0 (the product is 0.0
> under any sign convention) — the unification prevents the sign *helper* itself
> from diverging. The macro duplicate copy (`src/macro/data_loader.py:167-193`)
> was brought into guard-parity with the canonical Module #5 `calculate_rsrs` in
> S002-002; the macro copy is NOT a third canonical implementation but a delegated
> copy that must mirror Module #5. This is recorded as an amendment here rather
> than a new ADR because the canonical formula declares the Python implementation
> authoritative (`design/cdd/micro-momentum-scanner.md` §4.1), so a sign-convention
> pin is a property of that existing formula, not an independent architecture
> decision. No ADR Status change.
>
> **Open follow-up (NOT closed by S002-001, discovered 2026-06-12 during the
> parity test):** the DuckDB views compute `ROW_NUMBER() OVER (... ORDER BY date
> DESC) AS rn` then `REGR_SLOPE(rn, close)`, whose sign is INVERTED relative to
> the Python scalar path for every monotonic series (a perfectly increasing
> series yields RSRS −1.0 from the view but +1.0 from Python). This is independent
> of the zero-boundary convention and requires a `data/views.sql` rn-ordering
> change plus view re-materialization — out of scope for S002-001. Tracked as a
> follow-up; pinned by the strict `xfail` in
> `tests/migration/test_rsrs_view_sign_convention.py`.

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| New and legacy code diverge | Medium | High | Migrate workflow by workflow and add regression tests. |
| Untracked migration work is lost | Medium | High | Preserve source Git status in import docs and commit source work before cleanup. |
| Interfaces bypass services during pressure | Medium | Medium | Add control manifest rules and code-review checks. |
| External API changes break workflows | Medium | Medium | Keep retries, caching, and explicit integration tests. |

## Performance Implications

| Metric | Before | Expected After | Budget |
|--------|--------|----------------|--------|
| MCP common query latency | Direct helper/database calls | Similar or slightly higher through service/repository boundaries | Under 30 seconds per current MCP timeout |
| API route latency | Direct DB access | Similar with reusable repositories | No regression visible to local operator |
| Memory | Interface-specific reads | Bounded service/repository reads | Avoid full-history UI loads |
| Test speed | Harder to isolate | Faster unit-level service tests | Keep common tests suitable for local iteration |

## Migration Plan

1. Freeze current state in CDD import docs.
2. Keep root MCP/API/CLI/GUI entrypoints working while introducing service-backed paths.
3. Move database access behind repository adapters.
4. Route MCP tools through core services.
5. Route FastAPI and UI workflows through the same service contracts.
6. Add tests for each migrated workflow.
7. Remove legacy compatibility code only after equivalent paths pass tests.

**Rollback plan**: Keep legacy entrypoints until replacement workflows pass tests. If a migrated service breaks a workflow, route that interface back to the legacy implementation while fixing the service contract.

## Validation Criteria

- [ ] `pytest` passes for MCP, database, and transport tests in the source repository.
- [ ] MCP stdio and SSE startup paths still work.
- [ ] FastAPI routes that expose migrated workflows use services/repositories instead of opening DB connections directly.
- [ ] Web build/type checks pass for the Vue console when API contracts change.
- [ ] No new interface code introduces scattered `sys.path.insert` or repeated project-root discovery.

## CDD Requirements Addressed

| CDD Document | System | Requirement | How This ADR Satisfies It |
|--------------|--------|-------------|----------------------------|
| `design/cdd/product-concept.md` | Layered Interfaces | GUI, web, CLI, API, and MCP should share domain services rather than fork business rules. | Establishes service/port boundaries and requires interface routing through shared contracts. |
| `design/cdd/module-index.md` | Clean Architecture Migration | Existing working flows should keep functioning while architecture is cleaned up. | Defines incremental migration, compatibility shims, verification gates, and rollback behavior. |

## Related

- `docs/imports/my-doge-micro/git-snapshot-2026-06-11.md`
- `docs/imports/my-doge-micro/current-state-2026-06-11.md`
- `docs/reference/python/VERSION.md`
- Source `docs/MODULARIZATION_PLAN.md`

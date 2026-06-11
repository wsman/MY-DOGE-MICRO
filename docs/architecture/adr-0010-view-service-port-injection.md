# ADR-0010: View-Service Port Injection (IMarketViewRepository)

## Status

Proposed

> **Promotion gate (S002-011 governance review, 2026-06-12).** This ADR stays
> Proposed for Sprint 002 even though its validation gate **IS met**.
> **MET (fully realized)**: `IMarketViewRepository` is declared in
> `src/doge/core/ports/market_view.py`; `DuckDBMarketViewRepository` wraps a
> read-only `DuckDBConnection` in
> `src/doge/infrastructure/database/market_view_repository.py`; all four
> services (`ViewService`, `RankingService`, `BreadthService`, `AnomalyService`)
> take the port as a REQUIRED arg with no infrastructure import (AC-2 grep
> clean); the composition root `src/doge/core/services/composition.py` is the
> single infrastructure-import site; the three MCP tool files use the
> `build_*()` factories.
> **REMAINS**: none at the contract level — the gate is satisfied. The ADR is
> brand-new this sprint, so self-promotion in the same commit window is
> intentionally deferred.
> **Recommend promotion at `/architecture-review` (Wave-4)** — the decision is
> fully realized; the FRESH Wave-4 review should confirm rather than this
> sprint self-promoting in the same window.

## Date

2026-06-12

## Last Verified

2026-06-12

## Decision Makers

WSMAN (lead-programmer), Codex (recon)

## Summary

The four read-only view-backed services (`ViewService`, `RankingService`,
`BreadthService`, `AnomalyService`) are converted from depending on the concrete
`DuckDBConnection` adapter to depending on a new **`IMarketViewRepository`**
port with a single `execute(sql, params) -> DataFrame` method. A composition
root (`src/doge/core/services/composition.py`) becomes the single site that
imports infrastructure and wires the `DuckDBMarketViewRepository` adapter. This
removes a standing clean-architecture layer violation and resolves OQ-5 / TR-041
/ AC-9.

## Engine Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python 3.10+, DuckDB 1.4.4, pandas 2.2.3 |
| **Domain** | Core architecture, service/port boundaries |
| **Knowledge Risk** | LOW — uses only existing DuckDB/pandas APIs already in the codebase |
| **References Consulted** | `src/doge/core/services/{view,ranking,breadth,anomaly}_service.py`, `src/doge/infrastructure/database/duckdb.py`, ADR-0001 |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | Unit test (`tests/unit/core/services/test_view_services_port_injection.py`) asserts each service takes a fake `IMarketViewRepository`, delegates `execute`, imports no infrastructure, and remains unit-testable with no DuckDB connection |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0001 (Accepted) — its `:125` "exact method signatures owned by implementation stories" escape hatch is what this ADR fills |
| **Enables** | clean-architecture-migration AC-2 / AC-9 closure; S002-011 ADR gate definitions |
| **Blocks** | New core.services code may no longer import `DuckDBConnection` directly (the grep-able invariant now holds for all of `core/services/`) |
| **Ordering Note** | S002-011 owns promotion to Accepted; the service rewrite + tests are authored now so promotion is mechanical |

## Context

### Problem Statement

Four core services (`ViewService`, `RankingService`, `BreadthService`,
`AnomalyService`) injected the **concrete** `DuckDBConnection` adapter directly
instead of a port, violating the layer rule at
`clean-architecture-migration.md:264-271` ("core.services may NOT import
infrastructure"). Only `StockService` was compliant. ADR-0001:125 permits this
as an interim step ("exact method signatures owned by module CDDs /
implementation stories"). The open decision (AC-9 / OQ-5) was: convert to a
port OR amend ADR-0001 to permit adapter-injection for view-backed read services.

### Current State

- Each of the four services (verified at `view_service.py:6,12-13`,
  `ranking_service.py:5,11-13`, `breadth_service.py:5,11-13`,
  `anomaly_service.py:5,11-13`) did `from doge.infrastructure.database.duckdb
  import DuckDBConnection`, took `conn: DuckDBConnection | None = None` in its
  constructor, and self-constructed `or DuckDBConnection(read_only=True)`.
- The DuckDBConnection surface they used is a tiny uniform
  `execute(sql, params) -> DataFrame` (verified at the 4 service call sites).
  They do NOT use `connect()`/context-manager/`refresh_views`.
- `StockService` (`stock_service.py:9,15`) is the compliant reference shape
  (takes `IStockRepository`, delegates to it, imports no infrastructure).

### Constraints

- A naive INJECT-PORT edit that merely changes the type hint still leaves
  `or DuckDBConnection(...)` in the constructor — the service module still
  imports infrastructure, so AC-2 (grep "no `from doge.infrastructure` in
  core/services") still fails. Default construction MUST move to a composition
  root.
- The four services are pure read-only view SELECTs with identical construction
  pattern — a single port with one `execute` method covers all four cheaply.
- `ViewService.list_views` has a per-view swallow-and-continue `except Exception`
  that must be preserved (affects the `mcp__doge-db__list_views` tool output).
- `AnomalyService` hardcodes `vw_volume_anomalies_cn` (no market param) — out of
  scope to change.

### Requirements

- All four services depend on a port, not on `DuckDBConnection`.
- No `from doge.infrastructure` import remains in any of the four service
  modules (AC-2 / `clean-architecture-migration.md:501-504`).
- A single composition root owns the infrastructure import and the default-adapter
  construction.
- Interface layers (MCP tools) construct services via the factory, not by wiring
  adapters directly.
- Behavior is preserved (ViewService JSON envelope, Ranking/Breadth/Anomaly row
  delegation).

## Decision

**INJECT-PORT via a single shared `IMarketViewRepository`.**

1. **`IMarketViewRepository`** (new, `src/doge/core/ports/market_view.py`) — a
   single abstract method `execute(self, sql: str, params: list | None = None)
   -> pd.DataFrame`. This one method covers all four read-only view services
   (per-domain ports like `IRankingViewRepository` would add 4 ABCs for no
   behavioral gain, since the SQL is service-owned).
2. **`DuckDBMarketViewRepository`** (new,
   `src/doge/infrastructure/database/market_view_repository.py`) — wraps a
   read-only `DuckDBConnection` and delegates `execute` to `conn.execute`. The
   adapter is a thin execution handle; it owns no SQL.
3. **Convert the 4 services**: each constructor now takes
   `view: IMarketViewRepository` as a REQUIRED arg (no default). REMOVE the
   `from doge.infrastructure.database.duckdb import DuckDBConnection` import
   from all four. The services import no infrastructure.
4. **Composition root** (`src/doge/core/services/composition.py`) — factory
   functions `build_view_service()`, `build_ranking_service()`,
   `build_breadth_service()`, `build_anomaly_service()` that construct a
   `DuckDBMarketViewRepository(read_only=True)` and inject it. **This module is
   the single site that imports `doge.infrastructure`** for these services.
5. **MCP tools** (`src/doge/interfaces/mcp/tools/{views,ranking,anomaly}.py`)
   call the factory functions instead of constructing with `DuckDBConnection`.

### Architecture

```
   MCP tools (interfaces)  --->  build_*() factories  (composition root)
                                        |
                                        v
                          IMarketViewRepository  (port, core/ports)
                                        ^
                                        |
                          DuckDBMarketViewRepository  (adapter, infrastructure)
                                        |
                                        v
                          DuckDBConnection (read-only DuckDB + attached SQLite)

   ViewService / RankingService / BreadthService / AnomalyService  (core/services)
        take IMarketViewRepository, delegate execute(sql, params)  -- NO infra import
```

### Key Interfaces

```python
# src/doge/core/ports/market_view.py  (NEW)
class IMarketViewRepository(ABC):
    @abstractmethod
    def execute(self, sql: str, params: list | None = None) -> "pd.DataFrame": ...

# src/doge/core/services/ranking_service.py  (CONVERTED)
class RankingService:
    def __init__(self, view: IMarketViewRepository):  # required, no default
        self._view = view
    def rsrs(self, market="cn", top=20):
        df = self._view.execute(f"SELECT * FROM vw_rsrs_ranking_{market} LIMIT ?", [top])
        return df.to_dict(orient="records")
# (identical shape for Breadth/Anomaly/View)
```

### Implementation Guidelines

- Service constructors take the port as a REQUIRED positional arg (no `= None`
  default, no `or DuckDBConnection(...)` fallback). The composition root supplies
  the default.
- The composition root is the ONLY module under `core/services/` that imports
  `doge.infrastructure`. It is permitted because it is pure wiring, not business
  logic.
- Do NOT add SQL to `DuckDBMarketViewRepository`; it stays a thin execution
  handle.
- Preserve `ViewService.list_views` per-view `except Exception` swallow behavior.
- Preserve `AnomalyService`'s hardcoded `vw_volume_anomalies_cn` view name.

## Alternatives Considered

### Alternative 1: AMEND-ADR (codify the DuckDBConnection-injection exception)

- **Description**: Amend ADR-0001 to formally permit read-only view-backed
  services to depend on `DuckDBConnection` as a documented exception.
- **Pros**: Avoids a new port + adapter + service rewrite; codifies the existing
  shape.
- **Cons**: A permanent carve-out that weakens the grep-able layer invariant
  (`clean-architecture-migration.md:266`); every future reviewer and
  `/architecture-review` must learn the exception; the four services keep
  importing infrastructure.
- **Estimated Effort**: Less now; permanent invariant cost.
- **Rejection Reason**: The four services use a tiny uniform `execute->DataFrame`
  surface and identical construction pattern; `StockService` already proves the
  port-injection shape works. The amend option trades short-term effort for a
  permanent carve-out.

### Alternative 2: Per-domain ports (`IRankingViewRepository` etc.)

- **Description**: Four ABCs, one per service.
- **Pros**: Maximally specific contracts.
- **Cons**: 4 ABCs for no behavioral gain, since the SQL is service-owned and the
  execution surface is identical.
- **Estimated Effort**: More ABCs + adapters.
- **Rejection Reason**: Single shared port with one `execute` method covers all
  four.

## Consequences

### Positive

- All of `core/services/` now satisfies AC-2 (grep "no `from doge.infrastructure`"
  holds for the 4 service modules).
- The four services are unit-testable with a fake repository (no DuckDB
  connection needed).
- The composition root is the single infrastructure-import site — grep-able and
  swappable (e.g. for tests or an alternate analytical store).
- AC-9 / OQ-5 / TR-041 are resolved.

### Negative

- One new ABC + adapter + factory module to maintain.
- MCP tool construction changes from `Service(DuckDBConnection(read_only=True))`
  to `build_service()` — a call-site churn in 3 tool files.

### Neutral

- `DuckDBConnection` is still used (now behind the adapter), so its behavior is
  unchanged.

## Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| A future service author re-introduces `DuckDBConnection` in `core/services/` | Medium | Medium | The composition root is documented as the single wiring site; the AC-2 grep gate is the CI guard |
| `ViewService.list_views` per-view swallow behavior regresses | Low | Medium | Unit test pins the JSON envelope shape including `rows: None` for failing views |

## Performance Implications

| Metric | Before | Expected After | Budget |
|--------|--------|---------------|--------|
| Query latency | DuckDB direct | Identical (same adapter, one extra method call) | <30s per MCP tool (technical-preferences.md) |
| Memory | Unchanged | Unchanged | Bounded by view result size |

## Migration Plan

1. **Done (this story)**: Declare `IMarketViewRepository` + `DuckDBMarketViewRepository`;
   convert the 4 services to required-port construction; add composition root;
   update the 3 MCP tool files to use factories.
2. **S002-011**: Promote this ADR to Accepted; update AC-9/OQ-5 to Resolved.

**Rollback plan**: The port/adapter/factory are additive. To roll back,
re-add `from doge.infrastructure.database.duckdb import DuckDBConnection` to the
four services and restore the `or DuckDBConnection(read_only=True)` default;
the port and adapter can remain (harmless).

## Validation Criteria

- [ ] Each of `ViewService`/`RankingService`/`BreadthService`/`AnomalyService`
      accepts a fake `IMarketViewRepository` in its constructor and delegates
      `execute(sql, params)`.
- [ ] None of the four service modules contains `from doge.infrastructure`
      (asserted via source inspection).
- [ ] The composition root constructs `DuckDBMarketViewRepository(read_only=True)`
      and is the single infrastructure-import site.
- [ ] `RankingService.rsrs`, `BreadthService.breadth`, `AnomalyService.anomalies`,
      and `ViewService.list_views` produce their documented outputs against a
      fake repository returning canned DataFrames.

## CDD Requirements Addressed

| CDD Document | System | Requirement | How This ADR Satisfies It |
|-------------|--------|-------------|--------------------------|
| `design/cdd/clean-architecture-migration.md` | clean-architecture-migration | AC-2: no `from doge.infrastructure` in `core/services/` | The 4 services import only the port; the composition root owns the infrastructure import |
| `design/cdd/clean-architecture-migration.md` | clean-architecture-migration | AC-9 / OQ-5: reconcile the 4 view-backed services | Converted to `IMarketViewRepository` port injection + composition root |
| `design/cdd/market-data-storage.md` | market-data-storage | §4.2 core service inventory: service constructor signatures | Constructors now take the port, not `DuckDBConnection` |

## Related

- Fills the ADR-0001:125 escape hatch for the four view-backed services.
- Refines **ADR-0001**'s Key Interfaces block (`:108-123`) by adding
  `IMarketViewRepository` to the port inventory.
- Resolves **TR-041** / **OQ-5** / **AC-9**.
- Code: `src/doge/core/ports/market_view.py`,
  `src/doge/infrastructure/database/market_view_repository.py`,
  `src/doge/core/services/composition.py`,
  `src/doge/core/services/{view,ranking,breadth,anomaly}_service.py`,
  `src/doge/interfaces/mcp/tools/{views,ranking,anomaly}.py`.

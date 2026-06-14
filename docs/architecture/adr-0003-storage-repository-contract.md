# ADR-0003: Storage Repository Contract (No Direct SQLite/DuckDB in Interface Layers)

## Status

Accepted

## Date

2026-06-11

## Last Verified

2026-06-12

## Decision Makers

WSMAN, Codex (proposal); pending lead-programmer / python-specialist review

## Summary

MY-DOGE-MICRO's storage layer (5 SQLite files + 1 DuckDB analytical file + `views.sql`) is currently accessed both through a clean `IStockRepository` / `IReportRepository` port surface and through direct `sqlite3.connect(...)` / `duckdb.connect(...)` calls in legacy and interface modules. This ADR decides that **all storage access — read and write — must go through repository adapters behind the ports declared in `src/doge/core/ports/repository.py`, with no direct SQLite or DuckDB imports in any interface layer (`src/api`, `src/doge/interfaces`, `src/interface`, MCP, web)**. It also records two HIGH-RISK operational properties of the current write path that must be remediated as part of honoring the contract: a destructive non-configurable `retention_days=180` and a swallowed write exception.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python 3.10+, SQLite (stdlib `sqlite3`), DuckDB 1.4.4 (+ sqlite extension), pandas |
| **Domain** | Data persistence, analytical reads, migration boundary |
| **Knowledge Risk** | LOW — uses long-stable `sqlite3` / `duckdb` APIs current in the pinned stack (`docs/reference/python/VERSION.md`) |
| **References Consulted** | `src/doge/core/ports/repository.py`, `src/doge/infrastructure/database/{duckdb,sqlite,repositories}.py`, `src/micro/database.py`, `data/views.sql`, `src/doge/config/settings.py`, ADR-0001 |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | `pytest` for repository contract tests; `grep` assertion that no interface module imports `sqlite3`/`duckdb` |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0001 (Accepted) — defines the layer rules and forbidden patterns this ADR operationalizes for storage |
| **Enables** | Future ADRs for MCP transport strategy (ADR-0004?), API surface stabilization, and the formal `Cache` port |
| **Blocks** | Any new interface story that opens a SQLite/DuckDB connection directly is blocked until routed through repositories |
| **Ordering Note** | Legacy free functions in `src/micro/database.py` remain as compatibility shims until each calling workflow (scanner, API router, dashboard) is migrated and tested |

## Context

### Problem Statement

Storage is the highest-risk foundation module. Today, two access shapes coexist:

1. **Clean (target)**: `IStockRepository` / `IReportRepository` ports in `src/doge/core/ports/repository.py`, implemented by `DuckDBStockRepository` and `SQLiteReportRepository` in `src/doge/infrastructure/database/repositories.py`, using `DuckDBConnection` and `SQLiteConnection` adapters.
2. **Legacy (current live path)**: `src/micro/database.py` opens SQLite directly; `src/api/routers/scan.py`, `src/micro/market_scanner.py`, and `src/interface/dashboard.py` import `save_stock_data_custom` / `init_db_custom` directly; `src/ai_analysis` and `market_scanner._refresh_duckdb_views` call the legacy `connect_duckdb()` shim.

This split means ADR-0001's forbidden patterns (`direct_sqlite_import_in_interface`, `direct_duckdb_connect_in_interface`, `_PROJECT_ROOT_recalculation`) are still violated by the live write path. It also means the destructive `retention_days=180` and the swallowed `except Exception: pass` in `save_stock_data_custom` (`src/micro/database.py:118-155`) are reachable from interface layers with no logging and no config override.

The cost of not deciding is that every new interface (MCP tool, API route, web view) re-opens storage directly, duplicating connection logic, retention policy, and error handling — and silently losing data.

### Current State

- Ports: `IStockRepository`, `IReportRepository` exist and are partially implemented.
- Adapters: `DuckDBConnection` (zero-copy SQLite attach, read-only default), `SQLiteConnection` (row-factory support) exist and are reused.
- Repositories: `DuckDBStockRepository`, `SQLiteReportRepository` cover prices/overview/sync-state and reports/notes/names.
- Legacy write path: `save_stock_data_custom(retention_days=180)` swallows exceptions; `initialize_system_dbs` recomputes `_PROJECT_ROOT`.
- Analytical reads: 8 DuckDB views (`vw_daily_enriched_cn`, `vw_rsrs_ranking_cn/us`, `vw_market_breadth_cn/us`, `vw_volume_anomalies_cn`, `vw_cross_sectional_return_cn`, `temp_vol_check`) defined in `data/views.sql`, refreshed after each scan.
- `Cache` port mentioned by ADR-0001 is not yet declared; `JSONTickerNameCache` is used inline by `get_overview`.

### Constraints

- Local-first: SQLite/DuckDB files remain the source of truth; no external DB.
- Brownfield continuity: the scanner workflow must keep working throughout migration.
- SQLite single-writer + no WAL today; concurrency is fragile.
- The destructive retention and the silent write-error swallow are existing behavior that must be remediated without losing data.

### Requirements

- Storage access from any interface layer is exclusively via repository methods behind ports.
- All DB paths are resolved through `DBConfig` (`Settings().db`), never recomputed.
- Write errors are logged and surfaced as typed exceptions, never swallowed.
- Retention is configurable via env (`DOGE_RETENTION_DAYS`) with a documented safe range.
- Analytical views remain zero-copy reads over the SQLite files.

## Decision

Adopt the **Storage Repository Contract**:

1. **Boundary rule**: interface modules (`src/api/**`, `src/doge/interfaces/**`, `src/interface/**`, MCP server, web backend) MUST NOT import `sqlite3` or `duckdb`, and MUST NOT call `sqlite3.connect` / `duckdb.connect`. They depend on `IStockRepository` / `IReportRepository` (and, when formalized, `ICache`).
2. **Adapter ownership**: `src/doge/infrastructure/database/` is the only place that opens SQLite/DuckDB connections. `DuckDBConnection` and `SQLiteConnection` are the connection managers; `DuckDBStockRepository` / `SQLiteReportRepository` are the adapters.
3. **Path ownership**: `DBConfig` (via `get_settings()`) is the only source of DB paths. Legacy `_PROJECT_ROOT` recomputation in `database.py` is tech debt to remove.
4. **Write-error contract**: every write path raises a typed `StorageWriteError` (to be introduced) or returns a structured result; bare `except Exception: pass` is forbidden in storage code.
5. **Retention contract**: `retention_days` is configurable via `DOGE_RETENTION_DAYS` (default 730 to satisfy the widest view window), documented as destructive, and applied per-ticker on write. The default migration lifts the silent 180-day ceiling.
6. **Concurrency contract**: SQLite is single-writer; enable WAL + `busy_timeout`; DuckDB analytical reads are read-only by default; `refresh_views` is the sole DuckDB writer.
7. **Legacy compatibility**: `src/micro/database.py` free functions remain as compatibility shims but receive no new callers; they are deleted once every caller (scanner, API, dashboard) is routed through repositories and tested.

### Architecture

```
MCP / API / CLI / Dashboard / Web
        |  (depend only on ports)
        v
  IStockRepository   IReportRepository   (ICache — to be formalized)
        ^                     ^
        |                     |
  DuckDBStockRepository   SQLiteReportRepository   (adapters)
        |                     |
  DuckDBConnection        SQLiteConnection         (connection managers)
        |                     |
  market.duckdb          cn/us/research .db        (files)
  + views.sql            governed by DBConfig
  (zero-copy ATTACH of cn/us .db)
```

### Key Interfaces

```python
# src/doge/core/ports/repository.py (existing)
class IStockRepository(ABC):
    def get_prices(self, ticker: str, market: str, days: int = 20) -> List[dict]: ...
    def get_overview(self, ticker: str, market: str) -> dict: ...
    def get_sync_state(self, tickers: List[str]) -> dict[str, dict]: ...

class IReportRepository(ABC):
    def list_macro_reports(self, limit: int = 100) -> List[dict]: ...
    def get_macro_report(self, report_id: int) -> Optional[dict]: ...
    def save_macro_report(self, *, content, risk_signal, volatility, tags, analyst) -> None: ...
    def save_research_report(self, *, title, content, tags, analyst) -> None: ...
    def add_note(self, *, ticker, content, market, note_type, title, tags, price_at_note, source) -> int: ...
    def search_notes(self, query: str, limit: int = 50) -> List[dict]: ...
    def list_stock_names(self) -> List[dict]: ...

# To be added by this contract (proposed, not yet implemented)
class IStockRepository(ABC):  # extension
    def save_prices(self, market: str, frame: "pd.DataFrame") -> int: ...   # returns rows appended
    def delete_older_than(self, market: str, ticker: str, cutoff_date: str) -> int: ...

class StorageWriteError(RuntimeError): ...
```

### Implementation Guidelines

- Add a repository-level `save_prices` that wraps the legacy `save_stock_data_custom` logic, reads `DOGE_RETENTION_DAYS`, and raises `StorageWriteError` instead of swallowing.
- Move `retention_days`, `MAX_DAYS`, and `BATCH` into `DBConfig`/`MarketConfig` with documented safe ranges (registry entries; see CDD §4.7).
- Enable SQLite WAL and `busy_timeout` inside `SQLiteConnection.connect`.
- Add a `Cache` port (`ICache`) and route `JSONTickerNameCache` behind it.
- Add a static check (CI grep) forbidding `import sqlite3` / `import duckdb` / `sqlite3.connect` / `duckdb.connect` under `src/api/`, `src/doge/interfaces/`, `src/interface/`.

## Alternatives Considered

### Alternative 1: Keep direct storage access in interfaces

- **Description**: Continue letting `src/api/routers/scan.py` and `market_scanner.py` import `database.py` directly.
- **Pros**: Zero migration cost.
- **Cons**: Perpetuates ADR-0001 forbidden patterns; the swallowed-exception and destructive-retention risks remain uncontrolled; every new interface duplicates connection logic.
- **Estimated Effort**: Lowest now, highest over time.
- **Rejection Reason**: Violates ADR-0001 and blocks testable, multi-interface growth.

### Alternative 2: Replace SQLite with DuckDB as the sole store

- **Description**: Write OHLCV directly to DuckDB tables, drop SQLite.
- **Pros**: One engine; richer SQL; no attach dance.
- **Cons**: DuckDB's concurrent-write story is weaker than SQLite WAL for a local-first single-operator tool; large behavioral change; loses zero-copy simplicity.
- **Estimated Effort**: High.
- **Rejection Reason**: Disproportionate to the problem; the boundary, not the engine, is the issue.

### Alternative 3: Keep dual access but add a lint rule only

- **Description**: No port enforcement; rely on code review to discourage direct imports.
- **Cons**: Non-deterministic; does not fix the destructive retention or swallowed errors.
- **Rejection Reason**: ADR-0001 already established the boundary; this ADR must make it enforceable.

## Consequences

### Positive

- One contract for all interfaces; behavior drift across MCP/API/CLI/Web is eliminated.
- Write errors become visible; retention becomes configurable and safe.
- Storage code becomes unit-testable via port fakes.
- Path bugs from `_PROJECT_ROOT` recomputation disappear.

### Negative

- Short-term duplication while legacy `database.py` and the repository adapters coexist.
- Migrating each caller (scanner, API, dashboard) is required before the legacy shims can be removed.
- Introducing `StorageWriteError` changes the failure mode callers see — they must handle it.

### Neutral

- The DuckDB file continues to hold only view definitions; OHLCV stays in SQLite (zero-copy unchanged).
- `JSONTickerNameCache` moves behind `ICache` but its on-disk format is unchanged.

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Caller migration stalls; legacy and repository paths diverge | Medium | High | Migrate workflow-by-workflow with regression tests; CI grep blocks new direct imports. |
| Changing `retention_days` default (180 → 730) surprises operators who expected pruning | Low | Medium | Document in release notes; keep env override; default change lands behind the same release that adds `DOGE_RETENTION_DAYS`. |
| WAL enablement changes lock behavior unexpectedly on Windows | Low | Medium | Test on the Windows target platform before rollout; provide rollback to default journal mode. |
| `save_prices` typed error breaks an unhandled caller | Medium | Medium | Audit callers in the same migration step; add try/except where the scan must continue. |

## Performance Implications

| Metric | Before | Expected After | Budget |
|--------|--------|----------------|--------|
| MCP common query latency | Direct helper/DB calls | Same or slightly higher through repository boundary | < 30s (MCP timeout) |
| Write latency (per ticker) | `to_sql` append + DELETE | Same (repository wraps identical SQL) | No regression |
| Memory | Pandas frames per call | Bounded by repository reads | Avoid full-history loads |
| Concurrency | Serialized, no WAL | WAL allows read-during-write | Operator-perceived snappier UI |

## Migration Plan

1. **Declare the contract** (this ADR → Accepted) and add the CI grep check (non-blocking warning initially).
2. **Add `save_prices` + `StorageWriteError` + `DOGE_RETENTION_DAYS`** to the repository; write unit + contract tests.
3. **Route `market_scanner.py`** through `IStockRepository.save_prices`; verify scan output unchanged.
4. **Route `src/api/routers/scan.py`** through the repository; remove its direct `database.py` import.
5. **Enable WAL + `busy_timeout`** in `SQLiteConnection`; test concurrent read/write.
6. **Formalize `ICache`** and route `JSONTickerNameCache` behind it.
7. **Delete legacy free functions** in `src/micro/database.py` once no callers remain; keep `initialize_system_dbs` only if it remains the bootstrapper (and rewrite it to use `DBConfig`).

**Rollback plan**: keep `src/micro/database.py` as a compatibility shim until every caller is migrated and tested. If a migrated workflow regresses, route that caller back to the legacy function and fix the repository contract before retrying.

## Validation Criteria

- [ ] `grep -rnE "import sqlite3|import duckdb|sqlite3\.connect|duckdb\.connect" src/api src/doge/interfaces src/interface` returns zero hits.
- [ ] `pytest` passes for repository contract tests (prices round-trip, report round-trip, PK violation raises, retention applies).
- [ ] A write that fails inside `save_prices` raises `StorageWriteError` and is logged (not swallowed).
- [ ] `DOGE_RETENTION_DAYS` is honored end-to-end; default documented.
- [ ] WAL is enabled and a concurrent DuckDB read does not block a SQLite write (and vice versa).
- [ ] All 8 analytical views enumerate correctly via `mcp__doge-db__list_views` after a refresh.

## CDD Requirements Addressed

| CDD Document | System | Requirement | How This ADR Satisfies It |
|-------------|--------|-------------|--------------------------|
| `design/cdd/market-data-storage.md` | Market Data Storage | "No interface layer opens a SQLite/DuckDB connection directly" (Acceptance Criteria, Migration) | Establishes the boundary rule and CI grep enforcement. |
| `design/cdd/market-data-storage.md` | Market Data Storage | "Write failures are logged, not swallowed" (Acceptance Criteria, Open Question #2) | Mandates `StorageWriteError` and forbids `except Exception: pass` in storage code. |
| `design/cdd/market-data-storage.md` | Market Data Storage | "Retention must be configurable" (Configuration Knobs, Open Question #1) | Introduces `DOGE_RETENTION_DAYS` with a safe default. |
| `design/cdd/module-index.md` | Clean Architecture Migration | "Centralize repositories and connection management behind ports" (High-Risk Modules mitigation) | Makes the repository/port boundary enforceable for storage. |

## Related

- ADR-0001 (Accepted) — Brownfield Clean Architecture Migration; this ADR operationalizes its storage-related forbidden patterns.
- `design/cdd/market-data-storage.md` — the module CDD this contract governs.
- Source: `src/doge/core/ports/repository.py`, `src/doge/infrastructure/database/{duckdb,sqlite,repositories}.py`, `src/micro/database.py`, `data/views.sql`, `src/doge/config/settings.py`.
- Future: ADR for the formal `Cache` port; ADR for MCP transport strategy once storage access is consolidated.

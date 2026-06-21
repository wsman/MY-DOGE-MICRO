# ADR-0004: Data Source Adapter Contract

## Status

Accepted (S004-004, 2026-06-14)

> **Promoted by S004-004 (TDX adapter implementation).** The S002-011 promotion
> gate is met: `TDXDataSource` implements `IMarketDataSource` without raising
> `NotImplementedError` (`src/doge/infrastructure/data_source/tdx.py`;
> `tests/test_tdx_adapter.py`, 26 tests, network-free); `tdx_downloader.py` is
> thin-wrapped as a CLI shim that constructs the adapter (Migration Plan step 4);
> the `sys.path.insert` / `_PROJECT_ROOT` block was removed in S002-005. The
> shared retry-helper extraction (`_retry.py`, Migration Plan step 2) is
> re-scoped to a follow-on — it is not a promotion gate (the S003-014 §ADR-0004
> gate item is the TDX implementation), so this ADR is Accepted with that
> consolidation deferred. A fresh `/architecture-review` (Sprint 004 Release
> gate) ruled the `connect(self, market="cn")` signature **acceptable** (review
> `architecture-review-s004-2026-06-14.md`): adapter signatures may add source-
> specific optional parameters provided they remain callable via the port
> contract — `market` defaults to `"cn"`, so `connect()` still satisfies
> `IMarketDataSource.connect(self) -> None`.
>
> **S014 follow-up (2026-06-21).** The canonical scan API no longer imports
> `src.micro.tdx_downloader` for server lists or server downloads. Server
> listing/testing is behind `ITDXServerList` / `ConfigTDXServerList`, and scan
> server downloads route through `ScanMarketUseCase` plus `TDXDataSource`
> (`tests/contract/test_no_micro_imports_in_interface.py`,
> `tests/unit/infrastructure/test_tdx_server_list.py`). Legacy downloader code
> remains as a compatibility surface and helper bridge inside infrastructure
> until a later deletion pass.

## Date

2026-06-11

## Last Verified

2026-06-21

## Decision Makers

WSMAN, Codex

## Summary

External market data access (TDX quotation servers and yfinance) must flow through adapters that implement the `IMarketDataSource` port defined in `src/doge/core/ports/data_source.py`, so that retry/backoff is shared, network calls tolerate offline/degraded operation, and every source normalizes to one canonical OHLCV frame. This ADR records that contract and the migration of the legacy `src/micro/tdx_*.py` modules and the ad-hoc `yfinance` calls in `src/macro/data_loader.py` onto it.

## Technology Compatibility

> This is a Product project. The "Engine Compatibility" table is interpreted as the Product Stack Compatibility table per `docs/CLAUDE.md`.

| Field | Value |
|-------|-------|
| **Stack** | Python 3.10+, opentdx (TDX protocol), yfinance 0.2.66, pandas, SQLite/DuckDB |
| **Domain** | Foundation — external market data ingestion |
| **Knowledge Risk** | MEDIUM — yfinance 0.2.66 changed session/proxy handling (see `src/macro/data_loader.py:48-50`); opentdx protocol behavior is empirical (raw `.day` mode deprecated) |
| **References Consulted** | `docs/reference/python/VERSION.md`, `src/micro/tdx_downloader.py`, `src/macro/data_loader.py`, `src/doge/core/ports/data_source.py`, `design/cdd/data-sources.md` |
| **Post-Cutoff APIs Used** | yfinance 0.2.66 download/Ticker API; opentdx `TdxClient.stock_kline` / `goods_kline` |
| **Verification Required** | Adapter unit tests must mock yfinance (no network) — `tests/test_yfinance_adapter.py`; TDX adapter migration verified by an integration smoke against a live server before deleting legacy paths |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0001 (Accepted) — defines the port/adapter layer and forbidden patterns this ADR enforces |
| **Enables** | Future ADRs for cache ports, repository contracts, and MCP/API routing through services |
| **Blocks** | New market-data ingestion stories must not bypass `IMarketDataSource` once their target adapter exists |
| **Ordering Note** | TDX adapter is implemented; remaining follow-up is legacy compatibility deletion and any final helper inlining, not ADR promotion |

## Context

### Problem Statement

The brownfield code accesses external market data from at least four unrelated places: `src/micro/tdx_loader.py` (local files), `src/micro/tdx_downloader.py` (TDX servers, direct SQLite writes), `src/macro/data_loader.py` (yfinance, with its own retry loop), and `src/micro/industry_analyzer.py` (yfinance `.info`). Each duplicates path discovery, ticker remapping, retry logic, and column normalization. This makes the offline/degraded behavior inconsistent, tests network-dependent, and prevents interface layers (MCP, API, UI) from swapping sources.

### Current State

- `IMarketDataSource` exists (`src/doge/core/ports/data_source.py`) with `connect/disconnect/download_kline/get_latest_market_date/is_connected`.
- `TDXDataSource` implements `IMarketDataSource` without required-method
  `NotImplementedError` and degrades to `None` when disconnected/offline
  (`src/doge/infrastructure/data_source/tdx.py`, `tests/test_tdx_adapter.py`).
- `ITDXServerList` / `ConfigTDXServerList` own configured server listing and
  connectivity checks without importing the legacy downloader.
- `YFinanceDataSource` did NOT exist — BUG B. It is now implemented (`src/doge/infrastructure/data_source/yfinance.py`) with a retry loop reused from `macro/data_loader.py`.
- Retry/backoff is implemented independently in `macro/data_loader.py` (3 retries, 5s delay, 429 token detection) and `industry_analyzer.py` (3 retries, 2s delay). These should converge.
- `tdx_downloader.py:23-26` uses `sys.path.insert` + `_PROJECT_ROOT` (ADR-0001 forbidden pattern).
- All sources emit slightly different column shapes; `_bars_to_df` adds `ticker`, the local loader does not, yfinance has no `amount`.

### Constraints

- Existing operator workflows (CLI `tdx_downloader.py`, macro refresh, AI industry analysis) must keep working during migration.
- yfinance requires HTTP/HTTPS proxy set via env vars (`macro/data_loader.py:48-60`) for CN network access — the adapter must not break that.
- TDX is the only reliable CN intraday/daily source behind the GFW; yfinance is the cross-listed/US fallback. Both must remain first-class.

### Requirements

- A single port (`IMarketDataSource`) that every external market data source implements.
- Shared, consistent retry/backoff behavior (bounded retries, rate-limit detection, degraded-not-crash outcome).
- One canonical OHLCV frame shape across all sources so downstream services do not branch on source.
- Network-free unit tests for every adapter (mock the third-party package).
- Offline/degraded tolerance: a failed source never corrupts local data or crashes the operator session.

## Decision

All external market data access is via adapter classes that implement `IMarketDataSource` under `src/doge/infrastructure/data_source/`. The contract is:

1. **Port-owned output schema**: `download_kline` returns `Optional[DataFrame]` with columns `date, open, high, low, close, volume, amount, ticker` (8 columns, in order) or `None` on degraded/empty.
2. **No raises for transient failure**: adapters catch network/rate-limit/empty errors and return `None`; only programmer errors (bad port usage) raise.
3. **Shared retry policy**: a bounded retry loop with rate-limit detection (tokens `Rate`, `429`, `Too Many Requests`) and a fixed backoff delay. Defaults: `max_retries=3`, `retry_delay=5.0s` (reused from `macro/data_loader.py`). Each adapter owns its own loop today; consolidation into a shared helper is an explicit follow-on (see Migration Plan).
4. **Lazy third-party import**: adapters `import yfinance` / `from opentdx...` inside the method body so unit tests can inject mocks and module import never touches the network.
5. **Source-specific gaps are documented, not hidden**: yfinance's missing `amount` is set to `0.0` and called out in the CDD; the yfinance `start` offset parameter is accepted-but-ignored (period API) and documented.
6. **Decoupled persistence**: adapters produce frames; the caller (a service in Module #2/#4) calls `save_stock_data_custom`. Adapters never open SQLite/DuckDB directly (ADR-0001 forbidden pattern `direct_sqlite_import_in_interface`).

### Architecture

```
MCP / API / CLI / UI
        |
        v
Core services (StockService, etc.)
        |
        v
IMarketDataSource (port)  <-- src/doge/core/ports/data_source.py
        ^                ^
        |                |
TDXDataSource      YFinanceDataSource      (future: akshare, etc.)
        |                |
        v                v
opentdx servers     yfinance (HTTP)        local TDX .day files
        |                |
        +-------+--------+
                |
                v
        save_stock_data_custom (Module #2)  --> stock_prices (SQLite)
```

### Key Interfaces

```python
# src/doge/core/ports/data_source.py (existing — unchanged by this ADR)
class IMarketDataSource(ABC):
    @abstractmethod
    def connect(self) -> None: ...
    @abstractmethod
    def disconnect(self) -> None: ...
    @abstractmethod
    def download_kline(self, ticker: str, market: str,
                       start: int = 0, count: int = 800) -> Optional[pd.DataFrame]: ...
    @abstractmethod
    def get_latest_market_date(self, market: str) -> Optional[str]: ...
    @abstractmethod
    def is_connected(self) -> bool: ...

# Adapter contract (enforced, not just convention):
# - download_kline returns the 8-column canonical frame or None
# - transient/empty/rate-limit errors -> None, never raise
# - third-party package imported lazily inside the method
```

### Implementation Guidelines

- New adapters live in `src/doge/infrastructure/data_source/<name>.py` and are exported from its `__init__.py`.
- Reuse the rate-limit token set from `macro/data_loader.py`; do not invent a new one.
- Normalize to lowercase canonical columns; flatten MultiIndex; coerce dtypes; drop NaN-OHLC rows.
- Add a network-free unit test in `tests/test_<name>_adapter.py` for: port conformance, column/dtype normalization, CN ticker remap (if applicable), empty-result handling, retry-then-succeed, and exhausted-retries-returns-None.
- Document any source-specific data gap (e.g. missing `amount`) in the CDD, not just in code.

## Alternatives Considered

### Alternative 1: Keep ad-hoc yfinance calls per consumer

- **Description**: leave `macro/data_loader.py` and `industry_analyzer.py` calling `yfinance` directly, each with its own retry loop.
- **Pros**: no migration work.
- **Cons**: retry/normalization drift; impossible to swap sources; tests stay network-bound.
- **Estimated Effort**: Lowest now, highest long-term.
- **Rejection Reason**: violates ADR-0001's service/port boundary and the offline-tolerance requirement.

### Alternative 2: Single mega-source that fans out internally

- **Description**: one `MarketDataSource` that internally decides TDX vs yfinance per ticker.
- **Pros**: one injection point for callers.
- **Cons**: hides source-specific failure modes; harder to test in isolation; couples CN-TDX and US-yfinance lifecycles.
- **Estimated Effort**: Medium.
- **Rejection Reason**: composable per-source adapters compose better and test better; a fan-out *service* can still be built on top later.

### Alternative 3: Repository-pattern only (no source port)

- **Description**: treat market data like storage — a single `StockRepository` that knows how to fetch-and-cache.
- **Cons**: conflates "read local" with "fetch remote"; makes offline/local-cache behavior unclear; the ADR-0001 layering separates repositories (local) from data sources (remote).
- **Rejection Reason**: ADR-0001 already distinguished `MarketDataSource` from `StockRepository`; collapsing them regresses that decision.

## Consequences

### Positive

- One normalization contract; downstream services stop branching on source.
- Network-free, deterministic adapter unit tests become possible (proven by `tests/test_yfinance_adapter.py`).
- Offline/degraded behavior is uniform: `None` from any source means "no new data," handled by callers.
- Adding a new source (e.g. akshare) is a bounded task: implement the port + add tests.

### Negative

- Two retry loops coexist until the shared helper is extracted (short-term duplication).
- Some legacy helper code remains reachable from the TDX compatibility path
  until a deletion pass retires it fully.
- yfinance `start` offset is accepted-but-ignored; callers needing offset semantics must use TDX.

### Neutral

- `amount` from yfinance is `0.0`; this is a permanent data-model quirk, documented in the CDD.

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Legacy TDX helper bridge outlives canonical routing | Medium | Medium | Keep it behind infrastructure adapters; layer gates forbid legacy imports from interface code |
| yfinance API change breaks adapter | Medium | Medium | Pin `yfinance==0.2.66` in `requirements.txt`; mock-based tests catch shape changes on dependency bump |
| Retry-policy drift before consolidation | Medium | Low | CDD section 7 records the canonical defaults; extract shared helper as first follow-on |
| Hidden data gap (amount=0) misleads consumers | Medium | Medium | CDD section 4.1 + 5 document it; consumers that weight by turnover must branch on source |

## Performance Implications

| Metric | Before | Expected After | Budget |
|--------|--------|---------------|--------|
| Per-ticker fetch latency | Same (network-bound) | Same | Under 30s (MCP tool timeout) |
| Memory per refresh | ~120 rows × N tickers | Same | Bounded by 120-day cap, no full-history loads |
| Offline run cost | Caller-dependent | Bounded: `max_retries × retry_delay` per ticker then `None` | 3 × 5s = 15s worst case per ticker |
| Test speed | Network-dependent, minutes | ~0.5s for 13 mocked tests (measured) | Local iteration friendly |

## Migration Plan

1. **DONE** — Implement `YFinanceDataSource` (BUG B) with shared retry heuristic and canonical normalization; add `tests/test_yfinance_adapter.py` (13 tests, all green).
2. **DONE** — Shared retry helper exists at `src/doge/infrastructure/data_source/_retry.py` and is used by the canonical adapters.
3. **DONE** — TDX adapter is implemented and sources servers/ports from `TDXConfig`; `tdx_downloader.py` no longer owns canonical API routing.
4. **PARTIAL** — Canonical scan API routes server downloads through `ScanMarketUseCase` and `TDXDataSource`; legacy downloader remains a compatibility shim/helper bridge.
5. **Consolidate yfinance `.info` metadata** — evaluate a `TickerMetadataSource` port for `industry_analyzer.py` metadata calls (separate ADR if adopted).
6. **Delete legacy paths** — only after each migrated workflow passes tests and a live smoke.

**Rollback plan**: Adapters are additive. If a migrated consumer breaks, route that consumer back to its direct call (`macro/data_loader.py`, `tdx_downloader.py`) while the adapter contract is fixed. The port and existing adapters stay in place.

## Validation Criteria

- [x] `IMarketDataSource` is implemented by both `TDXDataSource` and `YFinanceDataSource` (TDX implemented S004-004; yfinance done).
- [x] `tests/test_yfinance_adapter.py` passes with no network access (done — 13/13).
- [x] A network failure in any adapter returns `None`, never raises, and never corrupts `stock_prices` (done for yfinance + TDX; S004-004).
- [x] No adapter opens SQLite/DuckDB directly (yfinance: done; TDX: no `save_stock_data_custom`, S004-004).
- [x] `tdx_downloader.py` no longer contains `sys.path.insert` / `_PROJECT_ROOT` (removed S002-005; CLI block thin-wrapped to the adapter S004-004).
- [x] Canonical scan router has no direct legacy downloader import
  (`tests/contract/test_no_micro_imports_in_interface.py`).
- [x] Retry/backoff helper is centralized for canonical data-source adapters.

## CDD Requirements Addressed

| CDD Document | System | Requirement | How This ADR Satisfies It |
|--------------|--------|-------------|---------------------------|
| `design/cdd/data-sources.md` | TDX/YFinance Data Sources | "Produce a normalized frame shape regardless of source" (User Promise) | Port contract forces the 8-column canonical frame from every adapter. |
| `design/cdd/data-sources.md` | TDX/YFinance Data Sources | "Tolerate ... rate-limiting and offline operation by retrying ... degrading to no new data rather than crashing" (User Promise) | Decision items 2 and 3 mandate `None`-on-failure and shared bounded retry. |
| `design/cdd/data-sources.md` | TDX/YFinance Data Sources | "Never require the operator to re-derive project paths" (User Promise) | Adapters source config from `settings.py`; CDD section 8 records removal of `tdx_downloader.py:23-26`. |
| `design/cdd/module-index.md` | Clean Architecture Migration | "Route interface modules through core services and infrastructure adapters" | This ADR defines the infrastructure-adapter contract that the migration routes external data through. |

## Related

- [ADR-0001: Brownfield Clean Architecture Migration](adr-0001-brownfield-clean-architecture.md) — defines the port/adapter layer and forbidden patterns this ADR operationalizes.
- `src/doge/core/ports/data_source.py` — the port contract.
- `src/doge/infrastructure/data_source/yfinance.py`, `src/doge/infrastructure/data_source/tdx.py` — the adapters.
- `src/micro/tdx_loader.py`, `src/micro/tdx_downloader.py`, `src/macro/data_loader.py`, `src/micro/industry_analyzer.py` — legacy callers to migrate.
- `design/cdd/data-sources.md` — full module CDD.

# ADR-0009: Cache/Metadata Port Split (ITickerNameCache + ITickerMetadataSource)

## Status

Proposed

> **Promotion gate (S002-011 governance review, 2026-06-12).** This ADR stays
> Proposed for Sprint 002. **The decision itself is realized** (the split is
> not contested): `ITickerNameCache` is left unchanged in
> `src/doge/core/ports/cache.py`; `ITickerMetadataSource` is declared in
> `src/doge/core/ports/metadata.py`; the `YFinanceMetadataSource` stub in
> `src/doge/infrastructure/data_source/yfinance_metadata.py` mirrors the
> `TDXDataSource` stub pattern. **REMAINS** before the *implementation* is
> complete: the real yfinance-backed metadata adapter — migrate the
> `yf.Ticker(yf_ticker).info` call at `src/micro/industry_analyzer.py:190`
> (plus its in-memory `metadata_cache` and local retry loop at `:180-203`) onto
> `YFinanceMetadataSource.get_metadata`. That follow-on story removes the
> `NotImplementedError` and is the natural promotion trigger.
> **Recommend promotion at `/architecture-review` (Wave-4)** — the port-split
> *decision* is accepted; only the real adapter implementation is a follow-on.
> Self-promotion in the same Sprint-002 commit window is intentionally
> deferred so the FRESH Wave-4 review confirms.

## Date

2026-06-12

## Last Verified

2026-06-12

## Decision Makers

WSMAN (lead-programmer), Codex (recon)

## Summary

The single ambiguous "ticker name / cache" port space referenced by ADR-0001 as
`TickerMetadataSource`/`Cache` is resolved by **splitting into two distinct
ports**: `ITickerNameCache` (local-JSON ticker-name lookups) and
`ITickerMetadataSource` (remote yfinance `.info` name+sector lookups). They
differ by data source (local file vs network) and by returned shape (name
string vs name+sector dict). This refines ADR-0001's `TickerMetadataSource`
line and resolves OQ-2 / TR-042.

## Engine Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python 3.10+, yfinance 0.2.66 |
| **Domain** | Core architecture, data access ports |
| **Knowledge Risk** | LOW — pure ABC declarations + stdlib typing; no post-cutoff API surface |
| **References Consulted** | `src/doge/core/ports/cache.py`, `src/doge/infrastructure/cache/ticker_cache.py`, `src/micro/industry_analyzer.py:180-203`, ADR-0001, ADR-0004 |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | Port-inventory unit test (`tests/unit/core/ports/test_port_inventory.py`) asserts both ports exist, are abstract, have >=1 implementation, and `__all__` parity |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0001 (Accepted) — refines its `TickerMetadataSource` / data-source port inventory |
| **Enables** | ADR-0004 step 5 (consolidate yfinance `.info` metadata behind the now-declared port); ADR-0003's `ICache` reconciliation (S002-011 gate work) |
| **Blocks** | Migration of `industry_analyzer.py:190` onto a port (now unblocked once this ADR is Accepted) |
| **Ordering Note** | S002-011 owns promotion of this ADR to Accepted; stories referencing a Proposed ADR are auto-blocked, so the stub adapter + tests are authored now to make promotion mechanical |

## Context

### Problem Statement

ADR-0001 lists a single `TickerMetadataSource` under "Data source ports" and
does not separately list a `Cache` port. Yet the migration CDD
(`clean-architecture-migration.md:235-247`) framed `TickerMetadataSource` vs
`Cache` as "mutually-exclusive candidate names for the same port", and the
registry (`entities.yaml`) triple-listed them. The docs are internally
inconsistent on whether they are one port with two competing names or two
ports. This is OQ-2 / TR-042.

### Current State

- `ITickerNameCache` (`src/doge/core/ports/cache.py:7`) — three methods
  (`get(ticker)`, `load(market)`, `clear()`), returning a **name string**.
  Its single adapter `JSONTickerNameCache` (`ticker_cache.py:15`) is a
  thread-safe, lazy, **file-backed** JSON cache of `{code: name}`. Consumed by
  `repositories.py:48` and `query_stock.py:6` (both construct it directly).
- A second, **live network-calling** metadata consumer exists entirely separate
  from the local-JSON cache: `src/micro/industry_analyzer.py:190` calls
  `yf.Ticker(yf_ticker).info`, pulling BOTH name (shortName/longName, :192) AND
  sector (sector/industry, :193), with its OWN retry loop (:187-198) and its
  OWN in-memory `metadata_cache` dict (:180, :203).
- ADR-0004:206 explicitly defers "evaluate a `TickerMetadataSource` port for
  `industry_analyzer.py` metadata calls (separate ADR if adopted)".

### Constraints

- The local-JSON name cache and the remote `.info` metadata call return
  different shapes (name string vs name+sector dict) and have different failure
  modes (file I/O vs network/rate-limit). Forcing one port would either bloat
  the file-cache adapter or saddle the network adapter with file-IO.
- ADR-0001 must not be edited in place to reverse its decision (sprint risk
  row: supersede/amend formally); a refining ADR is the cleaner path.
- I-prefix naming drift (ADR-0001 un-prefixed `StockRepository`/`TickerMetadataSource`
  vs source `IStockRepository`/`ITickerNameCache`) is bundled into TR-042 but
  resolved separately (see Decision §I-prefix).

### Requirements

- Declare the two-port split so the registry can be made internally consistent.
- Provide a concrete (stub) implementation of `ITickerMetadataSource` so the
  port has an adapter to target, matching the existing `TDXDataSource` stub
  pattern (`tdx.py:32,35`).
- Resolve the I-prefix drift by recording an alias map, NOT by renaming
  existing ABCs (avoids touching `repositories.py:48` / `query_stock.py:6`
  imports).

## Decision

**SPLIT into two distinct ports.**

1. **`ITickerNameCache`** (`src/doge/core/ports/cache.py`) — left **exactly
   as-is**. It is the local-JSON ticker-name lookup port (get/load/clear),
   backed by `JSONTickerNameCache`. ADR-0001's separate `Cache` concept is
   understood to be this existing port; ADR-0003's proposed `ICache` is
   reconciled to it (formal ADR-0003 promotion is S002-011 scope).
2. **`ITickerMetadataSource`** (new, `src/doge/core/ports/metadata.py`) — the
   remote yfinance `.info` metadata port. Single method
   `get_metadata(ticker, market) -> Optional[dict]` returning
   `{'name': ..., 'sector': ...}`. Backed by a stub adapter
   `YFinanceMetadataSource` (`src/doge/infrastructure/data_source/yfinance_metadata.py`)
   whose `get_metadata` raises `NotImplementedError` with a pointer to
   `src/micro/industry_analyzer.py:190` — mirroring the `TDXDataSource` stub
   pattern. The real `.info` migration is a follow-on story.

ADR-0001:115's `TickerMetadataSource` line is **refined** (not superseded) by
this ADR: the un-prefixed `TickerMetadataSource` canonical name maps to the
new `ITickerMetadataSource` port; the `Cache` concept maps to the existing
`ITickerNameCache` port.

### I-prefix decision

KEEP the `I`-prefixed ABC names (`IStockRepository`, `ITickerNameCache`,
`ITickerMetadataSource`, `IMarketViewRepository`). Do NOT rename existing
ABCs. The registry (`entities.yaml`) records an alias map from ADR-0001's
un-prefixed names (`StockRepository`, `MarketDataSource`, `TickerMetadataSource`,
`Cache`) to the I-prefixed source names. This resolves the AC-10/OQ-2
naming-drift half without churn at the import sites.

### Architecture

```
                         +-----------------------------+
   local JSON file  ---> | ITickerNameCache            | <- JSONTickerNameCache
(get/load/clear, name)   |  (existing, unchanged)      |
                         +-----------------------------+

                         +-----------------------------+
   yfinance .info  ----> | ITickerMetadataSource       | <- YFinanceMetadataSource (stub)
(get_metadata, name+sec) |  (new, ADR-0009)            |
                         +-----------------------------+
```

### Key Interfaces

```python
# src/doge/core/ports/cache.py  (UNCHANGED)
class ITickerNameCache(ABC):
    def get(self, ticker: str) -> Optional[str]: ...
    def load(self, market: str) -> Dict[str, str]: ...
    def clear(self) -> None: ...

# src/doge/core/ports/metadata.py  (NEW)
class ITickerMetadataSource(ABC):
    @abstractmethod
    def get_metadata(self, ticker: str, market: str) -> Optional[dict]: ...
        # returns {'name': ..., 'sector': ...} or None
```

### Implementation Guidelines

- Do not add a network dependency to `JSONTickerNameCache`; it stays file-backed.
- Do not add file I/O to `YFinanceMetadataSource`; it stays network-only.
- The `get_metadata` return dict MUST carry at minimum `name` and `sector` keys
  (matching `industry_analyzer.py:192-193`); additional keys are permitted but
  not required by the contract.
- The stub adapter raising `NotImplementedError` counts as an implementation
  for port-coverage tests (same precedent as `TDXDataSource`).

## Alternatives Considered

### Alternative 1: NO-SPLIT (single port with richer method set)

- **Description**: One port (canonical name `ITickerNameCache` or
  `TickerMetadataSource`) whose adapter may be file-backed OR network-backed,
  with `get_name` + `get_sector` methods.
- **Pros**: Simpler registry (one entry); one fewer ABC.
- **Cons**: Bloats the file-cache adapter with a network method (or saddles the
  network adapter with file I/O); mixes two failure modes (file I/O vs
  network/rate-limit) behind one contract; contradicts ADR-0004:206 which
  already treats metadata as a separate future port.
- **Estimated Effort**: Slightly less code now; more coupling later.
- **Rejection Reason**: The verified evidence (live `.info` call returning
  sector the JSON cache lacks; different data sources) favors two ports.

## Consequences

### Positive

- The registry can be made internally consistent (no more triple-listing).
- The local-JSON cache and the remote metadata call evolve independently.
- `industry_analyzer.py:190` has a clear migration target.
- The I-prefix decision avoids churn at existing import sites.

### Negative

- One additional ABC + stub adapter to maintain until the real `.info` migration.
- ADR-0001:115 must be read as "refined by ADR-0009" — future readers must
  follow the cross-reference.

### Neutral

- `ITickerMetadataSource` has only a stub adapter until a follow-on story
  migrates the `.info` call (acceptable; same status as `TDXDataSource`).

## Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| Stub adapter has no real impl, so port-coverage test must tolerate stub | High | Low | Test asserts the stub raises `NotImplementedError` (counts as an impl); mirrors `TDXDataSource` precedent |
| Registry readers (`/architecture-review`, `/story-readiness`) still see ADR-0001's un-refined line | Medium | Low | ADR-0009 Decision explicitly states how ADR-0001:115 is read post-decision |

## Performance Implications

| Metric | Before | Expected After | Budget |
|--------|--------|---------------|--------|
| CPU | N/A (pure ABC) | N/A | N/A |
| Memory | N/A | N/A | N/A |
| Network | N/A (stub) | Unchanged until `.info` migration | N/A |

## Migration Plan

1. **Done (this story)**: Declare `ITickerMetadataSource` + stub
   `YFinanceMetadataSource`; export both ports from `ports/__init__.py`; leave
   `ITickerNameCache` unchanged.
2. **Follow-on**: Migrate `industry_analyzer.py:190` onto `YFinanceMetadataSource`
   (remove the in-memory `metadata_cache` dict and the local retry loop).
3. **S002-011**: Promote this ADR to Accepted as part of the ADR gate
   definitions; reconcile ADR-0003's `ICache` to `ITickerNameCache`.

**Rollback plan**: The split is additive. If it proves wrong, delete
`metadata.py` + `yfinance_metadata.py` and revert `ports/__init__.py`; the
existing `ITickerNameCache` is untouched.

## Validation Criteria

- [ ] `ITickerMetadataSource` and `ITickerNameCache` both exist and are abstract.
- [ ] Each port has >=1 implementation under `src/doge/infrastructure/`
      (`YFinanceMetadataSource` stub counts; `JSONTickerNameCache` exists).
- [ ] `ports/__init__.py` `__all__` includes both ports.
- [ ] Registry (`entities.yaml`) lists the two ports as DISTINCT, with the
      ADR-0001 alias map recorded.

## CDD Requirements Addressed

| CDD Document | System | Requirement | How This ADR Satisfies It |
|-------------|--------|-------------|--------------------------|
| `design/cdd/clean-architecture-migration.md` | clean-architecture-migration | AC-10 / OQ-2: reconcile ADR-0001 port names with source ABC names | Records the alias map (un-prefixed `TickerMetadataSource`/`Cache` -> `ITickerMetadataSource`/`ITickerNameCache`); keeps I-prefix |
| `design/cdd/clean-architecture-migration.md` | clean-architecture-migration | §4.1 port inventory: resolve mutually-exclusive framing | Declares the two as distinct ports, removing the "mutually-exclusive candidate names" language |
| `design/cdd/market-data-storage.md` | market-data-storage | OQ-7 (`ICache` port formalize?) | `ICache` == `ITickerNameCache`; a separate `ITickerMetadataSource` covers remote metadata |

## Related

- Refines **ADR-0001** (`docs/architecture/adr-0001-brownfield-clean-architecture.md`)
  — its `TickerMetadataSource` line is read as refined by this ADR.
- Enables **ADR-0004** step 5 (consolidate yfinance `.info` metadata).
- Cross-references **ADR-0003** (proposed `ICache` == `ITickerNameCache`;
  promotion in S002-011).
- Resolves **TR-042** / **OQ-2**.
- Code: `src/doge/core/ports/cache.py`, `src/doge/core/ports/metadata.py`,
  `src/doge/infrastructure/data_source/yfinance_metadata.py`.

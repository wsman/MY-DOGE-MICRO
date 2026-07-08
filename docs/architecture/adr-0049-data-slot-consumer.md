# ADR-0049: Data Slot Consumer

## Status

Accepted

## Date

2026-07-07

## Decision Makers

wsman (product owner) / implementation agent

## Summary

Sprint 040 consumes the `data` slot facet at the market remote data-source seam.
The sprint adds a slot-aware `DataSourceRegistry` and two built-in data slots:
`data.tdx` and `data.yfinance`.

When `DOGE_FEATURE_SLOT_PLATFORM` is off, `build_tdx_data_source()` still returns
the existing `TDXDataSource` directly. When the flag is on and no explicit TDX
server is requested, the same factory returns a `DataSourceRegistry` assembled
from data slot contributions. The default registration order keeps TDX first,
so scan behavior remains parity preserving unless a caller explicitly selects a
different source.

## Status Update - 2026-07-08

ADR-0058 makes the built-in Slot Platform consumer path default-on for local
runs, so the data-source registry path is now the default when no preferred TDX
server is supplied. The direct TDX fallback remains available through explicit
opt-out or preferred-server selection.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python 3.10+; existing market data-source ports; existing slot facet dataclasses |
| **Domain** | Market Intelligence, remote OHLCV data-source selection |
| **Knowledge Risk** | LOW - local wiring over existing TDX/yfinance adapters and existing `IMarketDataSource` seam |
| **References Consulted** | `docs/architecture/adr-0042-slot-platform.md`, `docs/architecture/adr-0043-slot-contribution-facets.md`, `docs/architecture/adr-0048-document-slot-consumer.md`, `src/doge/bootstrap/gateway_factories/market.py`, `src/doge/application/use_cases/scan_market.py`, `src/doge/core/ports/data_source.py`, `src/doge/platform/slots/facets.py`, `C:\Users\WSMAN\.claude\plans\openclaw-like-magical-barto.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | data slot unit tests, data-source registry tests, data slot parity tests, CLI/API/doged slot status tests, import boundaries, docs validators, maturity honesty, plan closure, whitespace checks |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0004 (Data Source Adapter), ADR-0042 (Slot Platform Foundation), ADR-0043 (Slot Contribution Facets), ADR-0045 (Slot Discovery Surfaces), ADR-0048 (Document Slot Consumer) |
| **Extends** | ADR-0043 by adding a runtime consumer for the `data_sources` facet |
| **Supersedes** | None |
| **Enables** | Later source policies, data health probes, data-source bundle composition, and SlotKernel data orchestration |
| **Blocks** | None |

## Context

`DataSourceContribution` already existed as a typed slot facet, but no runtime
factory consumed it. Market scanning still reached a single hardcoded
`build_tdx_data_source()` factory, and `ScanMarketUseCase` accepted only one
injected `IMarketDataSource`.

The existing use-case seam is sufficient for the first data consumer. A registry
can implement the same adapter shape and delegate per market/source without
changing the use-case contract or persistence loop.

## Constraints

- Keep `DOGE_FEATURE_SLOT_PLATFORM` default `false`.
- Preserve flag-off `TDXDataSource` construction and scan behavior.
- Preserve explicit `preferred_server` behavior by returning direct
  `TDXDataSource`.
- Keep `doge.platform.slots` pure and framework-free.
- Place concrete TDX/yfinance slot providers beside infrastructure adapters.
- Do not add live data health probes, active permission enforcement, source
  policy UI, source failover, caching, persistence schema changes, or
  ModelRouter/ProfileRegistry changes.
- Do not add Web Slot Center, SDK slot client, bundle activation, third-party
  install, signing, or SlotKernel lifecycle orchestration.
- Do not close external/operator gates or change production maturity posture.

## Decision

Add `doge.products.market.data_sources.DataSourceRegistry`. It consumes
`DataSourceContribution` values and exposes the existing market-data adapter
shape:

```python
def connect(self, market: str = "cn") -> None: ...
def disconnect(self) -> None: ...
def is_connected(self) -> bool: ...
def download_kline(self, ticker: str, market: str, start: int = 0, count: int = 800): ...
def get_latest_market_date(self, market: str): ...
```

The registry builds source instances from contribution factories, rejects
duplicate source IDs, rejects empty source sets, supports wildcard or explicit
markets, and raises `SlotConfigurationError` when no source supports the
requested market or preferred source. It also supports yfinance-style no-arg
`connect()` by falling back from `connect(market)` to `connect()`. Because the
existing use case only asks `is_connected()` without passing a market, the
registry also confirms the selected source and target market immediately before
`download_kline()` delegates.

Add `doge.infrastructure.data_source.slot.TDXDataSourceSlot` and
`YFinanceDataSourceSlot`. They declare `data.tdx` and `data.yfinance`, type
`data`, owner `market-intelligence`, capabilities `market_data.ohlcv` plus
provider-specific capabilities, and `network=allow`.

Add `build_slot_aware_data_source()` to
`src/doge/bootstrap/runtime_factories/slots.py`. It resolves data slots whose
feature flags are satisfied, rejects duplicate source IDs, and returns a
`DataSourceRegistry` or `None` when no data source contributions are enabled.

Update `build_tdx_data_source()` so it uses the slot-aware registry only when
slot platform is enabled and `preferred_server` is not set. Otherwise it returns
direct `TDXDataSource` exactly as before.

## Alternatives Considered

### Alternative 1: Change `ScanMarketUseCase` to accept `DataSourceRegistry`

- **Description**: Add a registry-specific parameter and selection logic to the
  use case.
- **Pros**: Makes registry semantics explicit at the use-case boundary.
- **Cons**: Widens application-layer knowledge of slot composition and creates
  unnecessary test churn.
- **Rejection Reason**: The existing `IMarketDataSource` shape is sufficient.
  The registry can preserve the use-case contract.

### Alternative 2: Put concrete data slots in `doge.products.market`

- **Description**: Place `data.tdx` and `data.yfinance` beside market product
  code.
- **Pros**: Source selection is visibly market-owned.
- **Cons**: Product code would import infrastructure adapters directly.
- **Rejection Reason**: The selection registry is product-owned, but concrete
  providers wrap infrastructure adapters and therefore belong beside those
  adapters.

### Alternative 3: Add a `DOGE_FEATURE_SLOT_DATA` flag

- **Description**: Gate data slot resolution behind a facet-specific flag.
- **Pros**: More granular rollout switch.
- **Cons**: Adds config lifecycle overhead for a parity-preserving TDX-first
  registry.
- **Rejection Reason**: `DOGE_FEATURE_SLOT_PLATFORM` is enough for this proof.
  Source policy and active health enforcement remain later work.

## Consequences

### Positive

- The `data` facet now has a real runtime consumer.
- Market scan wiring can receive data-source contributions without changing
  `ScanMarketUseCase`.
- Default flag-off behavior remains direct TDX construction.
- Default flag-on ordering keeps TDX first.
- Duplicate data-source IDs fail fast.
- Discovery surfaces list `data.tdx` and `data.yfinance`.

### Negative

- Source selection is simple ordered matching, not a full policy engine.
- Health and permissions remain declarative.
- No active failover or retry policy is added beyond existing adapters.
- The registry is assembled through current runtime factories rather than a
  first-class `SlotKernel`.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Data-source selection changes scan behavior | LOW | MEDIUM | Flag-off path remains direct TDX; flag-on default registers TDX before yfinance; parity tests cover factory and use-case behavior. |
| yfinance `connect()` signature differs from TDX | MEDIUM | LOW | Registry falls back from `connect(market)` to no-arg `connect()`. |
| Duplicate source IDs mask one provider | LOW | MEDIUM | Factory and registry reject duplicates with `SlotConfigurationError`. |
| Operators mistake data slots for live data readiness | LOW | MEDIUM | ADR/CDD/evidence keep health probes, source policy, failover, production gates, and maturity upgrade out of scope. |

## CDD Requirements Addressed

| CDD System | Requirement | How This ADR Addresses It |
|------------|-------------|--------------------------|
| `design/cdd/sprint-040-data-slot-consumer.md` | Data-source slots can contribute market data adapters consumed by scan wiring. | Adds `DataSourceRegistry`, `data.tdx`, `data.yfinance`, and slot-aware data source factory wiring. |
| `design/cdd/bc-02-market-intelligence.md` | Market Intelligence owns market data source selection and scanning behavior. | Keeps the selection registry in `doge.products.market` and preserves scan persistence behavior. |
| `docs/architecture/adr-0004-data-source-adapter.md` | Data adapters must remain behind ports and degrade locally. | Keeps TDX/yfinance adapters behind the existing market data-source shape. |

## Performance Implications

- **CPU**: one small market/source selection loop before each delegated source
  operation.
- **Memory**: one registry plus adapter instances when slot platform is enabled.
- **Load Time**: imports built-in data-source slot providers when the built-in
  slot registry is built.
- **Network**: no new network calls at construction; live network behavior
  remains inside existing adapters.

## Migration Plan

1. Add `DataSourceRegistry`.
2. Add `TDXDataSourceSlot` and `YFinanceDataSourceSlot`.
3. Register both data slots in the built-in slot registry.
4. Add `build_slot_aware_data_source()`.
5. Wire `build_tdx_data_source()` to use the registry only when slot platform is
   enabled and no preferred server is requested.
6. Extend CLI/API/doged slot discovery expectations for `data.tdx` and
   `data.yfinance`.
7. Keep health probes, source policy, failover, SlotKernel, bundles, loaders,
   signing, and third-party install deferred.

## Validation Criteria

- `data.tdx` and `data.yfinance` manifests are typed as `data`, declare
  `slot_platform`, and provide market data capabilities.
- With slot platform off, no slot-aware data-source registry is assembled and
  `build_tdx_data_source()` returns direct `TDXDataSource`.
- With slot platform on, default `build_tdx_data_source()` returns a
  `DataSourceRegistry` with TDX first.
- Explicit `preferred_server` keeps direct TDX construction even when the slot
  platform is enabled.
- Market scan use-case wiring can use a custom data slot registry.
- Duplicate source IDs fail fast.
- CLI/API/doged slot discovery lists `data.tdx` and `data.yfinance`.
- Maturity posture remains `production_ready: false`,
  `stable_declaration: forbidden`, and `level_3_sdk_platform: experimental`.

## Related Decisions

- ADR-0004: Data Source Adapter
- ADR-0042: Slot Platform Foundation
- ADR-0043: Slot Contribution Facets
- ADR-0045: Slot Discovery Surfaces
- ADR-0048: Document Slot Consumer

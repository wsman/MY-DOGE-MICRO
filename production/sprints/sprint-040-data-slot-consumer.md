# Sprint 040 - Data Slot Consumer

Status: Local implementation complete / ready for local acceptance
Date: 2026-07-07

## Summary

Sprint 040 implements the data-facet consumer slice from
`C:\Users\WSMAN\.claude\plans\openclaw-like-magical-barto.md`.

The sprint adds built-in `data.tdx` and `data.yfinance` slots and wires data
source contributions into the market remote scan data-source seam through a
slot-aware `DataSourceRegistry`. The default registry keeps TDX first, and the
flag-off factory path still constructs `TDXDataSource` directly.

This sprint makes market data sources an actual slot contribution point. It
does not complete the full OpenClaw-like Slot Platform.

## Scope

- Add ADR-0049 and this sprint CDD/governance trail.
- Add `DataSourceRegistry` in `doge.products.market.data_sources`.
- Add `TDXDataSourceSlot` and `YFinanceDataSourceSlot` in
  `doge.infrastructure.data_source.slot`.
- Register `data.tdx` and `data.yfinance` in the built-in slot registry.
- Add `build_slot_aware_data_source()` in
  `src/doge/bootstrap/runtime_factories/slots.py`.
- Wire `build_tdx_data_source()` to use slot-aware data sources only when
  `DOGE_FEATURE_SLOT_PLATFORM` is enabled and no preferred TDX server is
  supplied.
- Extend CLI, doged, and `/v1/slots` tests to cover data slot status.
- Add data slot unit tests, product registry tests, and data parity tests.
- Update the OpenClaw-like plan file.

## Explicitly Out of Scope

- Data source active health probes, circuit breakers, automatic failover, or
  source policy UI.
- TDX/yfinance behavior changes, caching, or persistence schema changes.
- Runtime permission enforcement for data slots.
- `SlotKernel`, `SlotLifecycle`, `SlotBundle`, `SlotPolicy`, or `SlotLoader`.
- `/v1/slot-bundles`, bundle activation, YAML manifests, third-party install,
  signing, or enterprise allowlist.
- Web Slot Center or SDK slot client source.
- ModelRouter/ProfileRegistry, external auth, or worker behavior changes.
- Production readiness declaration or external/operator gate closure.

## Registration

This sprint is not registered in `production/sprint-status.yaml`. It follows the
recent local platform sprint precedent where no new story-status tracking is
introduced.

## Verification Status

Local verification is recorded in
`production/qa/evidence/sprint-040-data-slot-consumer-manifest.md`.

Initial verification result:

- Data slot / registry / parity / discovery focused suite passed: 60 tests.

Final broad validation is recorded in the evidence manifest.

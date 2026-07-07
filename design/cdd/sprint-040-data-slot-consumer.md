# Sprint 040 CDD: Data Slot Consumer

Status: Ready for Acceptance
Date: 2026-07-07

## 1. Overview

Sprint 040 makes the Slot Platform consume the `data` facet for market
data-source selection.

The sprint adds built-in `data.tdx` and `data.yfinance` slots, a slot-aware
`DataSourceRegistry`, and factory wiring so remote market scans can use
slot-contributed sources when `DOGE_FEATURE_SLOT_PLATFORM` is enabled.

The sprint does not add active data health probes, failover policy, source
policy UI, caching, persistence migrations, or production data readiness.

## 2. User Promise / JTBD

A platform engineer can add market data-source slots without modifying
`ScanMarketUseCase`.

A market workflow owner can keep the current TDX-first behavior while gaining a
controlled contribution point for future data sources, source policy, and
bundle-driven data selection.

## 3. Detailed Behavior

- `DataSourceRegistry` lives in `doge.products.market.data_sources`.
- `DataSourceRegistry` accepts `DataSourceContribution` values.
- Each data source contribution must have a unique `source_id`.
- Data source factories are resolved against `SlotContext`.
- Source instances must expose the existing market data-source adapter shape:
  `connect`, `disconnect`, `is_connected`, `download_kline`, and
  `get_latest_market_date`.
- Source matching is market-aware and supports wildcard `*` markets.
- A preferred source ID can narrow selection.
- Unsupported markets or unknown preferred source IDs raise
  `SlotConfigurationError`.
- TDX-style `connect(market)` and yfinance-style no-arg `connect()` are both
  supported.
- `TDXDataSourceSlot` and `YFinanceDataSourceSlot` live in
  `doge.infrastructure.data_source.slot`.
- `data.tdx` contributes the existing `TDXDataSource`.
- `data.yfinance` contributes the existing `YFinanceDataSource`.
- The built-in slot registry registers `data.tdx` before `data.yfinance`.
- `build_slot_aware_data_source()` returns `DataSourceRegistry` when data
  source slots are enabled, otherwise `None`.
- `build_tdx_data_source()` uses the slot-aware registry only when
  `DOGE_FEATURE_SLOT_PLATFORM` is enabled and no preferred TDX server is
  supplied.
- CLI/API/doged slot discovery shows `data.tdx` and `data.yfinance` as resolved
  when slot platform is enabled.

## 4. Contracts / Data Model

Data source contribution:

```python
DataSourceContribution(
    source_id="data.tdx",
    factory=lambda context: TDXDataSource(),
    markets=("cn", "us"),
    capabilities=("market_data.ohlcv",),
)
```

Registry adapter shape:

```python
def connect(self, market: str = "cn") -> None:
    ...

def download_kline(
    self,
    ticker: str,
    market: str,
    start: int = 0,
    count: int = 800,
):
    ...
```

Feature flag:

```text
DOGE_FEATURE_SLOT_PLATFORM=1
```

No new feature flag is added for this sprint.

## 5. Edge Cases

- Slot platform off: direct `TDXDataSource` construction remains in use.
- Slot platform on: default registry source order is `data.tdx`,
  `data.yfinance`.
- Explicit `preferred_server`: direct `TDXDataSource` construction remains in
  use even when slot platform is on.
- Duplicate source ID: data-source assembly fails fast.
- Unknown preferred source ID: registry construction fails fast.
- Unsupported market: source lookup fails fast.
- Source factory returns `None`: registry construction fails fast.
- Source exposes no-arg `connect()`: registry falls back from `connect(market)`
  to `connect()`.
- Reused registry switches market: `download_kline()` reconnects the selected
  source for the requested market before delegating.

## 6. Dependencies

- ADR-0004 Data Source Adapter.
- ADR-0042 Slot Platform Foundation.
- ADR-0043 Slot Contribution Facets.
- ADR-0045 Slot Discovery Surfaces.
- ADR-0048 Document Slot Consumer.
- Existing `TDXDataSource`, `YFinanceDataSource`, and `ScanMarketUseCase`.

## 7. Configuration Knobs

- `DOGE_FEATURE_SLOT_PLATFORM`: default `false`; gates slot-aware market data
  source factory usage.

No `DOGE_FEATURE_SLOT_DATA` flag is introduced.

## 8. Acceptance Criteria

- Built-in registry includes `data.tdx` and `data.yfinance`.
- Data slot manifest/status is visible through `doge slots`, `doged slots`, and
  `/v1/slots`.
- Slot-aware data-source assembly returns no registry when slot platform is off.
- `build_tdx_data_source()` returns direct `TDXDataSource` when slot platform is
  off.
- `build_tdx_data_source(preferred_server=...)` returns direct `TDXDataSource`
  even when slot platform is on.
- `build_tdx_data_source()` returns a `DataSourceRegistry` with TDX first when
  slot platform is on.
- `ScanMarketUseCase` can be wired through a slot-contributed data-source
  registry without changing its constructor.
- Duplicate source IDs fail fast.
- No active health probes, source failover policy, runtime permission
  enforcement, Web Slot Center, SDK slot client, persistence schema, SlotKernel,
  SlotBundle, SlotPolicy, SlotLoader, third-party install, signing, or
  enterprise allowlist is added.
- Maturity posture remains `production_ready: false`,
  `stable_declaration: forbidden`, and `level_3_sdk_platform: experimental`.

## 9. Validation Plan

```bash
py -3 -m pytest tests/unit/platform/slots/test_builtin_data_slot.py tests/unit/products/market/test_data_source_registry.py tests/contract/test_data_source_slot_parity.py tests/cli/test_cli_slots.py tests/contract/test_slot_api.py tests/cli/test_doged_cli.py -q
py -3 -m pytest tests/unit/platform/slots tests/unit/products/market tests/contract/test_data_source_slot_parity.py tests/contract/test_document_slot_parity.py tests/contract/test_watcher_slot_parity.py tests/contract/test_governance_slot_parity.py tests/contract/test_workflow_slot_parity.py tests/contract/test_agent_backends_slot_parity.py tests/contract/test_tool_registry_slot_parity.py -q
py -3 tools/ci/sdk-contract-check.py
py -3 scripts/validate_import_boundaries.py
py -3 scripts/validate_docs_authority.py
py -3 scripts/validate_docs_links.py
py -3 scripts/validate_docs_maturity_claims.py
py -3 scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0049-data-slot-consumer.md
py -3 scripts/validate_alpha_maturity_honesty.py --file design/cdd/sprint-040-data-slot-consumer.md
py -3 scripts/validate_no_stale_counts.py
py -3 scripts/validate_adr_index_completeness.py
py -3 scripts/validate_governance_yaml_shape.py
py -3 scripts/validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/openclaw-like-magical-barto.md
git diff --check
cmd.exe /c git diff --check
```

## 10. Local Verification Result

Final local verification is recorded in
`production/qa/evidence/sprint-040-data-slot-consumer-manifest.md`.

## 11. Out of Scope

- Data source active health probes, circuit breakers, automatic failover, or
  source policy UI.
- TDX/yfinance behavior changes, caching, or persistence schema changes.
- Runtime permission enforcement for data slots.
- `SlotKernel`, `SlotLifecycle`, `SlotBundle`, `SlotPolicy`, and `SlotLoader`.
- `/v1/slot-bundles`, bundle activation, YAML manifests, third-party install,
  signing, or enterprise allowlist.
- Web Slot Center or SDK slot client source.
- ModelRouter/ProfileRegistry, external auth, or worker behavior changes.
- Production readiness declaration or external/operator gate closure.

# Sprint 040 - Data Slot Consumer Manifest

> Sprint: 040 (Data Slot Consumer)
> Date: 2026-07-07
> Status: Local implementation complete; verification passed.

## Scope

This manifest records local evidence for the data slot consumer sprint:
`data.tdx` and `data.yfinance` contribute existing market data-source adapters,
and the slot-aware runtime factory composes a `DataSourceRegistry` behind
`DOGE_FEATURE_SLOT_PLATFORM`.

## Implementation Evidence

| Area | Evidence |
|---|---|
| ADR | `docs/architecture/adr-0049-data-slot-consumer.md` records the data-consumer decision. |
| CDD | `design/cdd/sprint-040-data-slot-consumer.md` records behavior, contracts, and acceptance criteria. |
| Data source registry | `src/doge/products/market/data_sources.py` adds `DataSourceRegistry`. |
| Built-in data slots | `src/doge/infrastructure/data_source/slot.py` adds `TDXDataSourceSlot` and `YFinanceDataSourceSlot`. |
| Built-in registry | `src/doge/bootstrap/runtime_factories/slots.py` registers `data.tdx` and `data.yfinance`. |
| Data consumer | `src/doge/bootstrap/runtime_factories/slots.py` adds `build_slot_aware_data_source()`. |
| Gateway factory wiring | `src/doge/bootstrap/gateway_factories/market.py` uses the slot-aware registry when slot platform is enabled. |
| Infrastructure facade | `src/doge/infrastructure/data_source/__init__.py` exports the built-in data slot classes. |
| Unit tests | `tests/unit/platform/slots/test_builtin_data_slot.py` and `tests/unit/products/market/test_data_source_registry.py` cover manifest, contribution, selection, connect compatibility, and fail-fast behavior. |
| Contract tests | `tests/contract/test_data_source_slot_parity.py` covers flag posture, default TDX parity, preferred-server fallback, slot registry assembly, scan use-case wiring, and duplicate source fail-fast. |
| Slot discovery tests | `tests/cli/test_cli_slots.py`, `tests/cli/test_doged_cli.py`, and `tests/contract/test_slot_api.py` cover `data.tdx` and `data.yfinance` status. |
| Session state | `production/session-state/active.md` records Sprint 040 as the current local implementation. |
| Runtime maturity | `docs/progress/runtime-maturity.yaml` adds the data slot consumer evidence record. |

## Verification Commands

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

## Verification Results

| Gate | Result |
|---|---|
| Data slot / registry / parity / discovery focused suite | Passed: 60 tests, 2 existing FastAPI deprecation warnings. |
| Broader slot/data regression suite | Passed: 110 tests. |
| Architecture boundary gates | Passed: 24 tests. |
| SDK contract | Passed: 15 surfaces, 15 entity parity checks. |
| Import boundaries | Passed. |
| Docs authority | Passed. |
| Docs links | Passed: 107 markdown files. |
| Docs maturity claims | Passed. |
| ADR/CDD maturity guard | Passed for ADR-0049 and Sprint 040 CDD. |
| Stale counts / ADR index / governance YAML | Passed. |
| Plan closure | Acceptable controlled-open: 4 open gates, 2 passed gates. |
| Whitespace | Passed in WSL Git and Windows Git. |

## Posture

- Production posture unchanged: `production_ready: false`,
  `stable_declaration: forbidden`, `level_3_sdk_platform: experimental`.
- No external/operator gates are closed by this sprint.
- No SDK package source, Web source, persistence schema, ModelRouter,
  ProfileRegistry, source health probe, active failover, runtime permission
  enforcement, bundle activation, third-party slot install, signing, or
  enterprise allowlist is part of this sprint.
- Slot Platform remains experimental and feature-flagged off by default.
- Sprint 040 completes the data-facet consumer proof only; it does not complete
  the full OpenClaw-like Slot Platform.

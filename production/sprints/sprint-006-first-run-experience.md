# Sprint 006 — First-Run Experience + Architecture Completion

> **Stage**: Release · **Predecessor**: Sprint 005 (Release-Ready v1 tagged `v0.1.0`)
> **Milestone**: Post-Release polish (no milestone gate; stage remains Release)
> **Duration**: 2026-06-14 → 2026-06-14 · **Status**: **done**

## Goal

Complete the deferred Wave-5 hygiene items, finish the ADR-0009 `YFinanceMetadataSource`
adapter follow-on, and deliver a zero-config `python src/cli.py demo` command that
showcases bundled analytical data without requiring a `DEEPSEEK_API_KEY`.

## Story Backlog

| Story | Title | Status | Files |
|---|---|---|---|
| S006-001 | sys.path test-shim regression gate | done | `tests/unit/layer_gates/test_test_sys_path_shim_gate.py` |
| S006-002 | MCP error-text sanitization | done | `src/doge/interfaces/mcp/server.py`, `tests/contract/test_mcp_error_redaction.py` |
| S006-003 | `wmic` → CIM migration | done | `src/doge/interfaces/mcp/server.py`, `tests/contract/test_mcp_orphan_detection_cim.py` |
| S006-004 | `YFinanceMetadataSource` full adapter | done | `src/doge/infrastructure/data_source/yfinance_metadata.py`, `src/doge/core/services/composition.py`, `src/doge/interfaces/api/deps.py`, `tests/unit/core/ports/test_yfinance_metadata_source.py` |
| S006-005 | `industry_analyzer.py` port migration | done | `src/micro/industry_analyzer.py`, `tests/unit/micro/test_industry_analyzer_metadata_port.py` |
| S006-006 | `fetch_names.py` optional port migration | done | `src/ai_analysis/fetch_names.py`, `tests/unit/ai_analysis/test_fetch_names_metadata_port.py` |
| S006-007 | `demo` CLI subcommand | done | `src/cli.py`, `tests/cli/test_cli_demo.py` |
| S006-008 | Demo docs + consistency | done | `docs/GETTING_STARTED.md`, `docs/CLI.md`, `tests/cli/test_cli_arg_parsing.py` |

## Deferred / Out of Scope

- **ADR-0007 path 1a** auth + non-loopback CORS — conditionally deferred until deployment
  model changes from loopback.

## Definition of Done

- [x] All Must-Have stories completed and tested
- [x] `python -m pytest -q` green (617 passed / 5 skipped / 0 failed)
- [x] Web build green and 70 vitest passed
- [x] `python src/cli.py demo` runs without `DEEPSEEK_API_KEY`
- [x] §6 layer gate ZERO hits
- [x] ADR-0009 migration plan step 2 marked done
- [x] `YFinanceMetadataSource` no longer raises `NotImplementedError`
- [x] `fetch_names.py` migrated onto `ITickerMetadataSource` port (S006-006)

## Verification

```bash
python -m pytest -q
cd web && npm test
cd web && npm run build
python src/cli.py demo --market cn --top 3
```

## Related Artifacts

- Plan: `C:\Users\WSMAN\.claude\plans\mighty-brewing-spark.md`

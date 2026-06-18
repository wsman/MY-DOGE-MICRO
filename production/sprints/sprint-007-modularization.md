# Sprint 007 — Clean Architecture Modularization

> **Stage**: Release · **Predecessor**: Sprint 006 (`v0.2.1` released)
> **Milestone**: Modularization completion (no milestone gate; stage remains Release)
> **Duration**: 2026-06-14 → TBD · **Status**: **in_progress**
> **Design CDD**: [`design/cdd/sprint-007-modularization-plan.md`](../../design/cdd/sprint-007-modularization-plan.md)

## Goal

Introduce the missing `src/doge/application/` use-case layer, move the composition root out of `core/services`, migrate the remaining live legacy surface (`src/api/`, `src/cli.py`, `src/macro/cli.py`, `src/ai_analysis/`, `src/micro/`, `src/macro/`, `src/interface/`) onto port-backed application use cases, and establish layer gates that forbid interface-layer imports of legacy modules or database/network drivers. Legacy modules become thin shims in Sprint 007; actual deletion is deferred to Sprint 008.

## Story Backlog

| Story | Title | Status | Files | Blocking |
|---|---|---|---|---|
| S007-001 | Application contracts + composition boundary | done | `src/doge/application/`, `src/doge/core/ports/llm.py`, `src/doge/application/composition.py`, `src/doge/core/services/composition.py` | **Yes** |
| S007-003 | CLI demo/query migration | done | `src/doge/interfaces/cli/`, `pyproject.toml`, `src/cli.py` (shim), `src/macro/cli.py` (shim), `docs/CLI.md` | **Yes** |
| S007-002 | API scan workflow migration | done | `src/doge/interfaces/api/`, `src/api/` (shim) | **Yes** |
| S007-004 | `ai_analysis` DuckDB/SQLite helpers → repository | **done** | `src/doge/infrastructure/database/`, `src/ai_analysis/` (shim) | **Yes** |
| S007-005 | `micro.market_scanner` → `ScanMarketUseCase` | **done** | `src/doge/application/use_cases/scan_market.py`, `src/doge/core/ports/file_scanner.py`, `src/doge/infrastructure/data_source/tdx_file_scanner.py`, `src/micro/market_scanner.py` (shim) | **Yes** |
| S007-006 | `macro` report → `GenerateMacroReportUseCase` + `ILLMClient` | todo | `src/doge/application/use_cases/generate_macro_report.py`, `src/doge/infrastructure/llm/deepseek_client.py`, `src/macro/` (shim) | **Yes** |
| S007-007 | Update `docs/MODULARIZATION_PLAN.md` | todo | `docs/MODULARIZATION_PLAN.md` | No (advisory) |
| S007-008 | Layer gates + final regression | todo | `tests/unit/layer_gates/`, `tests/unit/application/`, `tests/cli/`, `tests/contract/` | **Yes** |

## Story Sequencing

```
S007-001 (foundation: contracts + composition root)
    │
    ├──► S007-003 (CLI migration)
    │        │
    │        └──► S007-002 (API migration)
    │                 │
    │                 ├──► S007-004 (ai_analysis cleanup)
    │                 │        │
    │                 │        ├──► S007-005 (market_scanner migration)
    │                 │        │
    │                 │        └──► S007-006 (macro report migration)
    │                 │
    │                 └──► S007-007 (docs update, parallel advisory)
    │
S007-008 (layer gates + regression) ◄───────────────────────┘
```

Implementation proceeds **story-by-story with user approval** after each story's tests pass.

## Deferred / Out of Scope

- **Actual deletion of legacy files** — deferred to Sprint 008. Sprint 007 only shims legacy modules.
- **ADR-0007 path 1a** auth + non-loopback CORS — remains conditionally deferred.
- **PyQt `db_editor.py`** — marked as `legacy_standalone`; no clean-arch migration planned.
- **Web UI changes** — web already consumes API; no web files are touched in Sprint 007.

## Definition of Done

- [x] S007-001 done: `src/doge/application/` exists, composition root in `doge.application.composition`, `doge.core.services` imports only `doge.core.ports`.
- [x] S007-003 done: `doge` console script works, `src/cli.py` and `src/macro/cli.py` are shims, bilingual output + secret redaction preserved, `docs/CLI.md` updated.
- [x] S007-002 done: `src/doge/interfaces/api/` is live surface, `src/api/` are shims, no direct sqlite3/duckdb in routers.
- [x] S007-004 done: `ai_analysis` files are shims, DuckDB/SQLite helpers live in infrastructure, no `from ai_analysis import` under `src/doge/`.
- [x] S007-005 done: `ScanMarketUseCase` exists and is tested, `src/micro/market_scanner.py` is a shim, local-file scanning logic lives in `doge.infrastructure.data_source.tdx_file_scanner`, API router local fallback uses the use case.
- [ ] S007-006 done: `GenerateMacroReportUseCase` + `ILLMClient` port + `DeepSeekClient` adapter exist and are tested, `src/macro/` are shims.
- [ ] S007-007 done: `docs/MODULARIZATION_PLAN.md` reflects Sprint 007 batches and deferred deletion plan.
- [ ] S007-008 done: all layer-gate tests pass and `python -m pytest -q` returns **617+ passed / 5 skipped / 0 failed / 0 error**.

### S007-005 Notes

- Local-file scanning migrated to canonical layers:
  - New port: `ITdxFileScanner` in `src/doge/core/ports/file_scanner.py`.
  - New adapter: `TDXFileScanner` in `src/doge/infrastructure/data_source/tdx_file_scanner.py` (self-contained; no `micro.*` import).
  - `ScanMarketUseCase` now orchestrates `ensure_schema` + `save_prices` and records per-ticker read/write failures without aborting.
  - `src/micro/market_scanner.py` is a thin shim delegating to `build_scan_market_use_case()`.
  - API router `_run_local_scan()` delegates to the use case.
- **Deferred** to S007-006/S007-008:
  - TDX server-download batch orchestration (still in `micro.tdx_downloader`).
  - `SQLiteStorageRepository` still delegates to `micro.database.save_stock_data_custom`.
  - `TDXDataSource` still delegates to `micro.tdx_downloader` helpers.
  - Macro router still imports `src.macro.*`.
- Layer gate `test_no_new_micro_imports_under_doge_except_legacy_allowlist.py` enforces that no *new* `micro` imports appear under `src/doge`; a small documented allowlist covers the deferred files above. The allowlist is temporary and will be removed once those files are migrated.

## Verification

## Verification

```bash
# Fast feedback (after each story)
python -m pytest tests/unit/layer_gates/ -q
python -m pytest tests/test_mcp_tools.py -q
python -m pytest tests/test_api_routers.py -q
python -m pytest tests/cli/ -q

# Full gate (S007-008 only)
python -m pytest -q
# Expected: 617+ passed, 5 skipped, 0 failed, 0 error

cd web && npm test && npm run build

# Manual smoke
python doge_mcp.py --transport stdio --log-level INFO
python -m uvicorn doge.interfaces.api.main:app --reload
python -m doge.interfaces.cli demo --market cn --top 5
```

## Related Artifacts

- Design CDD: [`design/cdd/sprint-007-modularization-plan.md`](../../design/cdd/sprint-007-modularization-plan.md)
- QA plan: [`production/qa/qa-plan-sprint-007.md`](../qa/qa-plan-sprint-007.md)
- Sprint status: [`production/sprint-status.yaml`](../sprint-status.yaml)
- Release context: [`production/releases/release-report-v0.2.1-2026-06-14.md`](../releases/release-report-v0.2.1-2026-06-14.md)

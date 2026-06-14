# QA Plan: Sprint 007 — Clean Architecture Modularization

**Sprint**: S007 — Clean Architecture Modularization  
**Date**: 2026-06-14  
**QA Lead**: python-specialist / lead-programmer  
**Baseline**: `python -m pytest -q` → 617 passed / 5 skipped / 0 failed / 0 error

---

## 1. Scope

This QA plan covers the brownfield modularization of MY-DOGE-MICRO's remaining legacy surface onto the `src/doge/application/` use-case layer. Scope includes:

- New application layer (`src/doge/application/contracts/`, `src/doge/application/use_cases/`)
- Composition root relocation (`doge.application.composition`)
- CLI migration (`src/doge/interfaces/cli/`)
- API migration (`src/doge/interfaces/api/`)
- `ai_analysis` / `micro` / `macro` shim migration
- Layer gates forbidding interface imports of legacy modules or DB/network drivers

Out of scope:

- Web UI functional changes (web already consumes API; only indirect impact)
- PyQt `db_editor.py` (legacy standalone tool)
- Actual deletion of legacy files (deferred to Sprint 008)

---

## 2. Test Strategy by Story

| Story | Required Evidence | Test Location | Gate Level |
|---|---|---|---|
| S007-001 | DTO frozen immutability; composition root imports only infrastructure; core/services imports only ports | `tests/unit/application/contracts/test_dtos.py`, `tests/unit/layer_gates/test_core_services_import_gate.py`, `tests/unit/layer_gates/test_composition_root_location.py` | BLOCKING |
| S007-003 | CLI commands delegate to use cases/services; exit codes preserved; bilingual output preserved; secret redaction preserved | `tests/cli/test_cli_service_dispatch.py`, `tests/cli/test_cli_exit_codes.py`, `tests/cli/test_cli_demo.py`, `tests/cli/test_bilingual_output.py`, `tests/cli/test_macro_cli_error_redaction.py` | BLOCKING |
| S007-002 | API routers delegate to use cases; SSE scan events preserved; no direct sqlite3/duckdb in routers | `tests/test_api_routers.py`, `tests/contract/test_api_scan.py`, `tests/contract/test_api_macro.py` | BLOCKING |
| S007-004 | DuckDB/SQLite helpers moved to infrastructure; `ai_analysis` shims only | `tests/unit/infrastructure/test_duckdb_adapter.py`, `tests/migration/test_views_sql.py`, `tests/unit/layer_gates/test_ai_analysis_shim_only.py` | BLOCKING |
| S007-005 | `ScanMarketUseCase` orchestration; `StorageWriteError` path; row-count parity | `tests/unit/application/use_cases/test_scan_market.py`, `tests/integration/test_scan_end_to_end.py` | BLOCKING |
| S007-006 | `GenerateMacroReportUseCase` + `ILLMClient` + `DeepSeekClient`; LLM failure path; report persistence | `tests/unit/application/use_cases/test_generate_macro_report.py`, `tests/unit/core/ports/test_llm_port.py`, `tests/unit/infrastructure/test_deepseek_client.py` | BLOCKING |
| S007-007 | Docs accurate, no orphaned references | Manual review checklist | ADVISORY |
| S007-008 | Full regression + layer gates green | `python -m pytest -q`, `cd web && npm test && npm run build`, manual smoke checks | BLOCKING |

---

## 3. Regression Scope

The following surfaces must remain green after every story merge:

1. **Full Python test suite** — `python -m pytest -q`
2. **Web build + tests** — `cd web && npm test && npm run build`
3. **MCP stdio startup** — `python doge_mcp.py --transport stdio --log-level INFO`
4. **API startup** — `python -m uvicorn doge.interfaces.api.main:app --reload`
5. **CLI demo** — `python -m doge.interfaces.cli demo --market cn --top 5`

Baseline: 617 passed / 5 skipped / 0 failed / 0 error.

---

## 4. Layer Gates

Sprint 008 introduces new layer-gate tests under `tests/unit/layer_gates/`:

| Gate | Assertion |
|---|---|
| `test_interface_import_gate.py` | `src/doge/interfaces/**/*.py` contains zero imports from `micro`, `macro`, `ai_analysis`, `src.api`, `src.interface`, `sqlite3`, `duckdb`, `yfinance`, `opentdx`, `openai` |
| `test_core_services_import_gate.py` | `src/doge/core/services/**/*.py` imports only `doge.core.ports` and allowed utilities; no `doge.infrastructure` imports |
| `test_composition_root_location.py` | `doge.application.composition` is the only module under `doge.application` that imports `doge.infrastructure`; `doge.core.services.composition` does not import infrastructure |
| `test_project_root_calculation.py` | Exactly one `_PROJECT_ROOT` calculation exists: `src/doge/config/settings.py` |
| `test_sys_path_insert_gate.py` | Zero `sys.path.insert` calls under `src/doge/` and `doge_mcp.py` |
| `test_ai_analysis_shim_only.py` | `src/ai_analysis/*.py` files contain no business logic beyond re-exports + `DeprecationWarning` |

---

## 5. Manual Smoke Checks

Run once after S007-008:

```bash
# MCP stdio (5-second check)
python doge_mcp.py --transport stdio --log-level INFO
# ^C after "=== SERVER START ==="

# MCP SSE
curl http://127.0.0.1:8902/health  # expect {"status":"ok"}

# API health
curl http://127.0.0.1:8901/api/health  # expect ok

# CLI surfaces
python -m doge.interfaces.cli --help
python -m doge.interfaces.cli demo --market cn --top 3
python -m doge.interfaces.cli rsrs --top 10
python -m doge.interfaces.cli breadth
```

---

## 6. Evidence Locations

| Evidence Type | Path |
|---|---|
| Automated test reports | `tests/unit/application/`, `tests/unit/layer_gates/`, `tests/cli/`, `tests/contract/`, `tests/integration/` |
| Manual smoke evidence | `production/qa/smoke/smoke-s007-*.md` (to be created after S007-008) |
| Regression baseline | This file + `design/cdd/sprint-007-modularization-plan.md` §8 |
| Layer-gate scripts | `tests/unit/layer_gates/` |

---

## 7. Acceptance Criteria

- [ ] All BLOCKING stories have focused test evidence that passes.
- [ ] Full suite returns **617+ passed / 5 skipped / 0 failed / 0 error**.
- [ ] Web build and vitest remain green.
- [ ] All layer gates in §4 pass.
- [ ] Manual smoke checks in §5 pass.
- [ ] No new `sys.path.insert`, no new direct sqlite3/duckdb in interface/application/core layers.
- [ ] Legacy modules are shims only (no new business logic).

---

## 8. Risk-Based Testing Notes

| Risk | Mitigation in QA |
|---|---|
| `market_scanner` regression on production data | Integration test compares row counts against pre-migration baseline. |
| Test monkeypatch breakage | Replace shim tests with clean-arch DI tests before deleting legacy modules. |
| Bilingual CLI output loss | `test_bilingual_output.py` asserts all preserved strings. |
| Secret redaction loss | `test_macro_cli_error_redaction.py` asserts no key in logs. |
| Circular import | Import-order tests for `doge.application` package. |
| TDX `NotImplementedError` | `ScanMarketUseCase` tests use mock `IMarketDataSource`; adapter tests remain separate. |
| Dual source of truth for DB paths | Parity test compares legacy constants against `Settings` for all 5 env vars. |

---

## 9. Sign-Off

| Role | Name | Verdict | Date |
|---|---|---|---|
| QA Lead | python-specialist | | |
| Lead Programmer | lead-programmer | | |
| Product Owner | operator | | |

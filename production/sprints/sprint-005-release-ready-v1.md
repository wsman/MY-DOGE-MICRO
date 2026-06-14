# Sprint 005 — Release-Ready v1 Tagging

> **Stage**: Release · **Predecessor**: Sprint 004 (Verification → Release clean PASS)
> **Milestone**: Release-Ready v1 baseline tagged `v0.1.0`
> **Duration**: 2026-06-14 → 2026-06-14 · **Status**: **done**

## Goal

Polish the Release baseline and tag **Release-Ready v1 (`v0.1.0`)**. Waves 1–4
land; Wave-5 hygiene items are intentionally deferred because they are
low-priority and one of them (test `sys.path` consolidation) was reverted after
an agent over-cleaned test imports.

## Story Backlog

| Story | Title | Status | Files |
|---|---|---|---|
| S005-001 | Traceability/manifest reconciliation + manifest gaps | done | `production/manifest.md`, traceability docs |
| S005-002 | SSE `str(e)` leak fixed to deterministic string | done | `src/doge/interfaces/mcp/server.py` |
| S005-003 | CLI bilingual remediation | done | `src/cli.py`, `docs/CLI.md` |
| S005-004 | User-test format reconciliation | done | `production/qa/evidence/user-tests/` |
| S005-005 | Retry consolidation (`_retry.py` + `YFinanceConfig`) | done | `src/doge/core/services/_retry.py`, YFinance data source |
| S005-006 | Macro engine routes through `YFinanceDataSource` adapter | done | `src/doge/core/services/composition.py`, macro engine |
| S005-007 | Macro adapter contract tests | done | `tests/integration/macro/test_data_loader_fetch_combined_via_adapter.py` |
| S005-008 | `scan.py` `list_distinct_tickers` via `IStockRepository` DI | done | `src/api/routers/scan.py`, `src/doge/infrastructure/repository/sqlite_storage.py` |
| S005-009 | `SQLiteStorageRepository` implements `list_distinct_tickers` | done | `src/doge/infrastructure/repository/sqlite_storage.py` |

## Deferred / Out of Scope

- **Wave-5a** test `sys.path` consolidation — reverted once; needs careful redo.
- **Wave-5b** MCP error-text sanitization.
- **Wave-5c** `wmic` → CIM migration.

## Definition of Done

- [x] Waves 1–4 complete and tested
- [x] `python -m pytest -q` green (579 passed / 4 skipped / 0 failed)
- [x] Web build green and 70 vitest passed
- [x] `v0.1.0` git tag created
- [x] `CHANGELOG.md` updated for Release-Ready v1
- [x] Stage remains `Release`

## Verification

```bash
python -m pytest -q
cd web && npm test && npm run build
git tag -a v0.1.0 -m "Release-Ready v1"
```

## Related Artifacts

- Changelog: `CHANGELOG.md`
- Active state: `production/session-state/active.md`

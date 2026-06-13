# Verification QA Plan — Sprint 003

> **Sprint**: Sprint 003 — Verification  
> **Date**: 2026-06-12  
> **Status**: Active  
> **Owner**: qa-lead  
> **Milestone**: [Verification / Release-Ready v1](../milestones/verification-milestone.md)  
> **Gate target**: Verification → Release

---

## Scope

This plan defines the **smoke coverage** required to exit Verification. It is
explicitly scoped to "does each surface start and respond correctly?" — not
deep functional testing, which is already covered by:

- **BLOCKING automated tests** (logic/integration/migration/API contract)
- **S003-002** — independent user-test evidence (`production/qa/evidence/user-tests/`)
- **S003-012** — performance baseline profile (`production/qa/evidence/perf/`)

### Boundary with sibling stories

| Story | Ownership | Evidence location | This plan's relationship |
|-------|-----------|-------------------|--------------------------|
| S003-002 | ux-designer / operator | `production/qa/evidence/user-tests/` | References; does not duplicate |
| S003-012 | performance-analyst | `production/qa/evidence/perf/` | References budgets; does not duplicate |
| S003-011 | qa-lead | `production/qa/smoke/smoke-2026-06-12.md` | Owns smoke execution records |

---

## Smoke Surface Matrix

| # | Surface | Launch command | Smoke action | Expected result | Automation | Notes |
|---|---------|----------------|--------------|-----------------|------------|-------|
| 1 | **FastAPI** | `python -m pytest tests/test_api_routers.py::TestHealthAndStats::test_health_returns_ok -v` | Invoke `/api/health` via `TestClient` | `200 {"status":"ok"}` | Automated | Contract-test evidence; no live socket |
| 2 | **CLI** | `python src/cli.py rsrs --top 10` | Run ranking subcommand | Tabulated top-10 table, exit 0 | Manual-smoke (automated CLI tests exist) | Requires data dir with DuckDB views |
| 3 | **Web** | `cd web && npm run build && npm test` | Typecheck + build + vitest | Build green, 49 tests passed | Automated | S002-012 fixed `@pretext` alias |
| 4 | **MCP** | `python doge_mcp.py --transport stdio --log-level INFO` | Start server; observe clean init | Process starts without traceback | Manual-smoke (automated MCP tool tests exist) | Stdio transport exits when stdin closes; SSE transport also valid |
| 5 | **PyQt** | `pytest tests/test_pyqt_smoke.py` | Import + basic window smoke | Skip or pass depending on Qt6 DLL availability | Advisory | **Known environment note**: `src/interface/dashboard.py:6` hardcodes a Qt6 DLL path; non-default installs may skip |

### Coverage vs. milestone exit criteria

The milestone requires smoke covering **3 surfaces (CLI / API / Web or MCP)**.
This plan covers **all 5 surfaces**, with PyQt marked advisory.

---

## Performance Budget Checks (referenced from S003-012)

See `standards/technical-preferences.md` Performance Budgets. S003-012 will
produce measured evidence against:

- MCP tool latency ≤ 30 s
- DB reads prefer DuckDB analytical views
- UI long-running tasks off main thread
- Memory bounded by local dataset size

This QA plan does **not** substitute for S003-012.

---

## Known Environment Notes

1. **PyQt6 DLL path**: `src/interface/dashboard.py:6` contains a hardcoded Qt6
   DLL path. On non-default environments the import may fail with
   `0xc0000139`; pytest marks the test skipped rather than failing the suite.
2. **DuckDB views**: CLI and MCP smoke require the DuckDB database and
   analytical views to be present. The commands below were run against the
   operator's local dataset.
3. **S002-013 key environment verification**: Macro / LLM paths require
   `DEEPSEEK_API_KEY` to be exported; smoke commands intentionally avoid those
   paths. A forensic audit confirmed no real key was ever committed to git
   history, so rotation/revocation is not required.

---

## Execution Evidence

| Artifact | Path |
|----------|------|
| Smoke report (this sprint) | `production/qa/smoke/smoke-2026-06-12.md` |
| Stale automated evidence (superseded) | `production/qa/evidence/source-pytest-2026-06-11.md` |
| Stale web build evidence (superseded) | `production/qa/evidence/web-build-2026-06-11.md` |

---

## Exit Criteria

- [x] QA plan document exists and covers ≥3 surfaces.
- [x] At least one smoke report exists with real-run records for ≥3 surfaces.
- [x] Stale evidence files are marked superseded.
- [x] Boundaries with S003-002 and S003-012 are documented.

---

## Related

- Sprint plan: `production/sprints/sprint-003-verification.md`
- Milestone: `production/milestones/verification-milestone.md`
- Performance budgets: `standards/technical-preferences.md`
- Stale evidence: `production/qa/evidence/source-pytest-2026-06-11.md`, `production/qa/evidence/web-build-2026-06-11.md`

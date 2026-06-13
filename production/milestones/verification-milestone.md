# Milestone: Verification / Release-Ready v1

> **Status**: Active  
> **Target Date**: 2026-06-26  
> **Stage**: Verification  
> **Sprint**: Sprint 003 — Verification  
> **Previous Milestone**: Implementation / Brownfield Modularization (Sprint 002 complete)

---

## Goal

Deliver the evidence and cleanup required to exit the Verification stage and pass the Verification → Release gate. The product is functionally complete; this milestone focuses on **validation, quality assurance, and architectural hygiene**.

## Exit Criteria

The milestone is complete when all of the following are true:

1. **User Validation Evidence**
   - [x] At least one documented operator workflow validation report exists in `production/qa/evidence/user-tests/`.
   - [x] Report covers an unguided end-to-end core workflow (e.g., scanner → report → archive).
   - [x] Three product validation sessions exist for the Verification → Release gate:
     - `user-test-001-2026-06-13.md` — core workflow.
     - `user-test-002-2026-06-13.md` — first-run / cold start.
     - `user-test-003-2026-06-13.md` — failure / recovery.

2. **QA / Smoke Evidence**
   - [x] `production/qa/qa-plan-verification.md` exists.
   - [x] At least one smoke report `production/qa/smoke/smoke-2026-06-*.md` covers 3 surfaces (CLI / API / Web or MCP).

3. **Performance Baseline**
   - [x] `production/qa/evidence/perf/perf-baseline-*.md` exists.
   - [x] Measurements compared against budgets in `standards/technical-preferences.md`:
     - MCP tool latency ≤ 30s
     - DB reads prefer DuckDB analytical views
     - UI long-running tasks off the main thread
     - Memory bounded by local dataset size

4. **Architecture Cleanup**
   - [ ] `src/api/routers/` and `src/api/main.py` contain no direct `sqlite3.connect` / `connect_duckdb` calls.
   - [ ] RSRS DuckDB view sign convention matches Python RSRS path.
   - [x] DDL for analytical views is under version control.

5. **Governance Decisions**
   - [x] ADR-0004 state finalized (Proposed with TDX deferral rationale, or Accepted).
   - [x] ADR-0007 state finalized (Proposed with CORS deferral rationale, or Accepted).
   - [x] Fresh `/architecture-review` session completed and documented.

6. **Quality Gates**
   - [x] `python -m pytest -q` green (0 failures).
   - [x] `cd web && npm run build` green.
   - [x] `cd web && npm test` green.
   - [ ] Layer-rule grep gates pass.

## Deferred to Post-Verification

| Item | Reason | Target |
|------|--------|--------|
| TDX adapter real implementation (`src/doge/infrastructure/data_source/tdx.py`) | User impact low; `tdx_downloader.py` remains functional; ADR-0004 promotion not a hard Release blocker | Post-Verification sprint |
| Test-bootstrap `sys.path` cleanup | Out of control-manifest scope | Wave 5 |
| MCP tool error-text sanitization | Hygiene suggestion | Wave 5 |
| `wmic` → CIM migration | Win11/Server 2025 portability, not current target | Wave 5 |

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| User-test scheduling slips | High | Start S003-002 on Day 1; operator self-walkthrough as fallback |
| API DI breaks legacy router tests | Medium | Incremental migration; contract tests |
| 2-week capacity insufficient | Medium | Cut order defined in Sprint 003 plan |

## Related Artifacts

- Sprint plan: `production/sprints/sprint-003-verification.md`
- Gate check report: `production/gate-checks/gate-implementation-verification-2026-06-12.md`
- Wave 4 readiness doc: `production/wave-4-review-readiness.md`
- Control manifest: `docs/architecture/control-manifest.md`
- S003-014 architecture review: `production/architecture-reviews/architecture-review-s003-014-2026-06-13.md`

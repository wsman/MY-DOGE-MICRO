# Code Review: Modular MCP Server (`src/doge/interfaces/mcp/`)

- **Date:** 2026-06-12
- **Scope:** `src/doge/interfaces/mcp/server.py` + `src/doge/interfaces/mcp/tools/{query_stock,ranking,anomaly,views}.py`
- **Why:** This server replaced the monolithic `mcp_server.py` as the LIVE `doge-db` MCP path (Wave 3b Batch-5). Highest-risk recent code — serves the operator's daily-use MCP tools.
- **Reviewers:** python-specialist, lead-programmer, qa-lead (parallel)
- **Final verdict:** **APPROVED WITH SUGGESTIONS** (after the 3 BLOCKING/Required fixes were applied + verified)

## Specialist Findings

### Language (python-specialist): ISSUES FOUND → resolved
- `[BLOCKING B-01]` `_unregister_pid` bare `except: pass` swallowed cleanup failures (corrupts PID file → false orphan warnings; also swallowed KeyboardInterrupt). **FIXED**: narrowed to `(OSError, ValueError)` + DEBUG log.
- `[BLOCKING B-02]` `stock_overview` opened two separate `sqlite3.connect()` without context managers → leak on exception. **FIXED**: consolidated to one `with`-block.
- `[WARNING W-01]` Raw exception text in tool responses (`server.py:184` `f"Error: {type}: {exc}"`) — can leak paths/SQL. *Suggestion*: sanitize to `{tool} failed [{cid}]`, keep detail in logs.
- `[WARNING W-02/W-03]` Windows `wmic` orphan detection is deprecated (removed on Win11/Server 2025); fails-open silently. *Suggestion*: migrate to CIM/PowerShell.
- `[WARNING W-04/W-05]` Module-level `REQUEST_COUNT`/`REQUEST_DURATION` mutation race under SSE concurrency; `REQUEST_DURATION` grows unbounded (memory leak). *Suggestion*: lock + `deque(maxlen=N)`.
- `[WARNING W-06]` `_fmt` duplicated 4× across modules. *Suggestion*: extract to shared helper.
- `[INFO I-01]` Import-time `LOG_DIR.mkdir` + `_setup_logging()` (test hazard). *Suggestion*: move to `main()`.

### Testability (qa-lead): GAPS
- `[BLOCKING B1 — Batch-6 gate]` `test_mcp_notes_softdelete.py` guards the LEGACY impl; modular `stock_overview` (which replicates the soft-delete fix) has **zero** soft-delete coverage. **Must retarget onto the modular tool BEFORE deleting `mcp_server.py`.**
- `[BLOCKING B2 — Batch-6 gate]` No 6-tool modular-vs-legacy output-parity test (only 2/6 live-probed). **Must exist BEFORE deletion.**
- `[WARNING W1]` Tool layer constructs repo/service internally — no DI seam; "unit" tests are DB-bound integration tests. *Suggestion*: add a private `_svc` param or a service-factory map on `create_mcp_server()`.
- `[WARNING W2-W6]` `_timed` timeout only tested on synthetic fn; lifespan DuckDB pre-warm failure path untested; `_detect_orphan_processes` (40 lines, platform-branched) zero coverage; `/metrics` format not pinned; integration tests assume an undocumented local fixture DB.
- **Positive:** `_timed` decorator error/timeout/correlation paths ARE well-covered; `TestPidManager` is exemplary isolated unit coverage; `/health` failure-path injection is the correct DI pattern.

### ADR Compliance (lead-programmer): DRIFT → resolved
- `[BLOCKING — ADR-0001]` `query_stock.py` constructed `DuckDBStockRepository(DuckDBConnection(...))` directly (interface→infrastructure), bypassing the composition root its 5 sibling tools use. **FIXED**: now calls `build_stock_service()`.
- `[WARNING]` Direct `sqlite3` notes/names reads in `stock_overview` — **justified transitional parity port** (ADR-0006:138 sanctions the raw notes read with `deleted_at IS NULL` mitigation; NoteRepository is Module #7's scope). *Track as tech-debt.*
- ADR-0006 transport strategy (6 tools, `_timed`+30s timeout, `"Error: …"` contract, parity coexistence): **COMPLIANT**.

## Standards Compliance: 6/6 (after fixes)
- [x] Public APIs documented · [x] complexity <10 · [x] methods <40 lines · [x] **DI via composition root (fixed)** · [x] config from settings · [x] interfaces exposed.

## Architecture & SOLID: CLEAN (after fixes)
- Dependency direction correct for all 6 tools (interface → composition → services → ports → infrastructure). The one bypass (`query_stock.py`) is fixed.
- SOLID: DIP restored (tools depend on the service abstraction via the factory, not concrete adapters). SRP on `stock_overview` is borderline but acceptable for a thin MCP adapter.

## Domain-Specific (Product): CLEAN
- **Schema safety:** parameterized SQL everywhere; the `deleted_pred` f-string is a constant from `PRAGMA table_info` (not user input) — safe.
- **Error handling:** sqlite errors caught + logged + graceful fallback (`暂无笔记`); tools never raise to the MCP client.
- **Config:** `get_settings()` used (no hardcoded paths). **Observability:** correlation-ID + structured logging + `/metrics`.
- **Resource cleanup:** DuckDB `read_only=True` everywhere (concurrent-safe); sqlite now context-managed (fixed).

## Fixes Applied (commit: "code-review fixes")
1. `query_stock.py` → `build_stock_service()` (composition root); removed interface→infrastructure imports.
2. `stock_overview` → one context-managed sqlite connection for names+notes.
3. `server.py _unregister_pid` → specific exception + DEBUG log (no bare except).

**Verification:** 493 passed/2 skipped/6 xfailed; `stock_overview` smoke green via composition root; `query_stock.py` grep-clean of `doge.infrastructure` imports.

## Carried Forward (tracked)
- **Wave-4 Batch-6 gates** (prerequisites for `mcp_server.py` deletion): retarget `test_mcp_notes_softdelete.py` to modular `stock_overview`; add 6-tool modular-vs-legacy parity test.
- **Suggestions backlog** (non-blocking): W-01 sanitize error text; W-02/03 `wmic`→CIM; W-04/05 metrics lock+cap; W-06 consolidate `_fmt`; I-01 move logging to `main()`; W1 tool-layer DI seam.

## Positive Observations
1. Correlation-ID via `contextvars` — idiomatic, thread/async-safe, trace-friendly.
2. Clean validation/decoration/dispatch separation; `ranking`/`anomaly`/`views` tools are exemplary (≤30 lines, composition-root only).
3. Soft-delete `PRAGMA table_info` detection is the correct defensive pattern for a schema that may or may not have `deleted_at` migrated.

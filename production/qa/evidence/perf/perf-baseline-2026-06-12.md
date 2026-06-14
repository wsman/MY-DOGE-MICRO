# Performance Baseline Report — 2026-06-12

> **Sprint**: Sprint 003 — Verification
> **Story**: S003-012 — Performance baseline profile
> **Date**: 2026-06-12
> **Environment**: Windows 10 IoT Enterprise LTSC 2021 (10.0.19044), Python 3.12.12, editable install (`pip install -e .`), local DuckDB 1.4.4 + SQLite stores
> **Operator**: Claude (automated profiling run)
> **Result**: **PASS** (8 / 8 surfaces within budget; every surface returned valid data)

Closes gate-check CONCERN **"Performance within budget"**.

---

## Summary

| Surface | Median | Budget | Verdict | Result shape |
|---------|-------:|-------:|:-------:|--------------|
| `mcp.tool:query_stock` | 223.43 ms | 30 000 ms | ✅ PASS | str len=2372, 21 lines |
| `mcp.tool:stock_overview` | 146.90 ms | 30 000 ms | ✅ PASS | str len=651, 15 lines |
| `mcp.tool:rsrs_ranking` | 384.39 ms | 30 000 ms | ✅ PASS | str len=2267, 21 lines |
| `mcp.tool:market_breadth` | 257.92 ms | 30 000 ms | ✅ PASS | str len=1088, 11 lines |
| `mcp.tool:volume_anomalies` | 262.63 ms | 30 000 ms | ✅ PASS | str len=1385, 21 lines |
| `mcp.tool:list_views` | 2 872.79 ms | 30 000 ms | ✅ PASS | str len=1301, 42 lines |
| `fastapi:/api/health` | 1.27 ms | 50 ms | ✅ PASS | HTTP 200 `{"status":"ok"}` |
| `cli:rsrs --top 10` | 865.32 ms | 30 000 ms | ✅ PASS | exit 0, 12 stdout lines |

**Overall: PASS** — 8 PASS, 0 FAIL, 0 ERROR of 8 surfaces. Largest measured
latency is `list_views` at ~9.6 % of its 30 s budget; every MCP/CLI surface
shows > 96 % headroom.

---

## Methodology

**Budgets** are sourced from `standards/technical-preferences.md`
("Performance Budgets") and `src/doge/interfaces/mcp/server.py`
(`TOOL_TIMEOUT = 30`):

- MCP common local queries: **<= 30 s** (the budget-relevant envelope).
- FastAPI per-request JSON overhead: **baseline; CORS preflight < 50 ms**.
- CLI: bounded to the same envelope as MCP (subprocess; exit code must be 0).

**What is timed — tool-body latency, not transport.** The 6 MCP tools are
measured by calling the tool-module async functions directly
(`asyncio.run(query_stock(...))`). The `@mcp.tool` wrapper in
`server.py` adds only input validation plus the `_timed` decorator, and the MCP
stdio framing adds negligible milliseconds of serialization. The tool-body
latency is therefore the 30 s-budget-relevant number; the transport layers
are not the budget surface and are intentionally out of scope for this
baseline.

**Reproducible inputs (deterministic; only timings vary):**

| Parameter | Value |
|-----------|-------|
| ticker | `000001.SZ` (Ping An Bank) |
| market | `cn` |
| `days` (query_stock) | 20 |
| `top` (rsrs / volume) | 20 |
| `breadth_days` (market_breadth) | 10 |
| `min_ratio` (volume_anomalies) | 3.0 |
| CLI `--top` | 10 |

**Warmup + median.** One warmup call is run per surface (DuckDB materializes
analytical views on first connection), then each surface is measured **5**
times and the **median** is reported. Timings are wall-clock via
`time.perf_counter` (in-process) / subprocess timing (CLI).

**"A fast tool that errored is not a pass."** Each measured result is validated
for shape (non-empty string, not an `Error:` sentinel, not a `No data` /
`No anomalies` empty-set sentinel) before a PASS verdict is recorded. An empty
or erroring result is reported as **ERROR** regardless of latency.

---

## Local-Only Invariant

Every profiled surface reads from the local DuckDB / SQLite stores via the
composition root (`doge.core.services.composition`). No network source
(yfinance / akshare / opentdx) is invoked by any surface in this
baseline. This was verified by reading the call chain before profiling:

| Tool module | Delegates to | Data source |
|-------------|--------------|-------------|
| `tools/query_stock.py` | `build_stock_service()` -> `StockService` -> `DuckDBStockRepository`; `stock_overview` also reads `stock_names` / `stock_notes` from the research SQLite | local DuckDB + SQLite |
| `tools/ranking.py` | `build_ranking_service()` / `build_breadth_service()` -> `*Service` -> `DuckDBMarketViewRepository` | local DuckDB |
| `tools/anomaly.py` | `build_anomaly_service()` -> `AnomalyService` -> `DuckDBMarketViewRepository` | local DuckDB |
| `tools/views.py` | `build_view_service()` -> `ViewService` -> `DuckDBMarketViewRepository` | local DuckDB |
| `api/main.py /api/health` | `DuckDBConnection(read_only=True).connect()` `SELECT 1` | local DuckDB |
| `cli.py rsrs` | `build_ranking_service()` -> `DuckDBMarketViewRepository` | local DuckDB |

The composition root (`src/doge/core/services/composition.py`) is the single
sanctioned site for infrastructure wiring (ADR-0010 AC-2); the service modules
import no network clients.

---

## Harness

**File**: `tools/perf/profile_baseline.py` (standalone; **not collected by
pytest** — lives under `tools/`, no `test_` functions).

**Invocation**:
```bash
python tools/perf/profile_baseline.py            # default: 5 runs/surface
python tools/perf/profile_baseline.py --runs 7   # tune sample size
python tools/perf/profile_baseline.py --json tools/perf/perf-baseline-2026-06-12.json
```

The harness times the 3 surface groups (6 MCP tool bodies, FastAPI
`/api/health` via Starlette `TestClient`, CLI `rsrs --top 10` via subprocess),
runs warmup + N measured runs, and prints the budget-comparison table above.
Exit code is 0 only if every surface returned valid data and stayed under
budget.

---

## Actual Output (this run, 2026-06-12)

Captured verbatim from `python tools/perf/profile_baseline.py --runs 5
--json tools/perf/perf-baseline-2026-06-12.json`:

```text
MY-DOGE-MICRO performance baseline profile
date=2026-06-12  python=3.12.12
platform=Windows-10-10.0.19044-SP0
inputs: ticker=000001.SZ market=cn days=20 top=20 breadth_days=10 min_ratio=3.0 cli_top=10
runs per surface (post-warmup): 5
budgets: mcp/CLI <= 30s, health < 50ms

[1/3] MCP tool bodies (budget <= 30000 ms) ...

[2/3] FastAPI /api/health (budget < 50 ms) ...

[3/3] CLI rsrs (budget <= 30000 ms) ...

Surface                           Median (ms)  Budget (ms)  Verdict  Runs  Result shape
---------------------------------------------------------------------------------------
mcp.tool:query_stock                   223.43        30000     PASS     5  str len=2372 lines=21
mcp.tool:stock_overview                146.90        30000     PASS     5  str len=651 lines=15
mcp.tool:rsrs_ranking                  384.39        30000     PASS     5  str len=2267 lines=21
mcp.tool:market_breadth                257.92        30000     PASS     5  str len=1088 lines=11
mcp.tool:volume_anomalies              262.63        30000     PASS     5  str len=1385 lines=21
mcp.tool:list_views                   2872.79        30000     PASS     5  str len=1301 lines=42
fastapi:/api/health                      1.27           50     PASS     5  HTTP 200 body={'status': 'ok'}
cli:rsrs --top 10                      865.32        30000     PASS     5  exit=0 stdout_lines=12

Overall: PASS  (8 PASS, 0 FAIL, 0 ERROR of 8 surfaces)
JSON snapshot written to tools/perf/perf-baseline-2026-06-12.json
```

Machine-readable snapshot: `tools/perf/perf-baseline-2026-06-12.json`.

---

## Per-Surface Notes

### MCP tool bodies (budget <= 30 000 ms)

All 6 tools pass with > 96 % headroom. Results confirm the tools return
real, non-empty result sets (not error sentinels):

- **query_stock** (223 ms) — 20-day OHLCV + indicators for `000001.SZ`, 21
  rendered lines.
- **stock_overview** (147 ms) — fastest MCP tool; name/sector + latest prices
  + notes in a single SQLite connection.
- **rsrs_ranking** (384 ms) — top-20 RSRS momentum table, 21 lines.
- **market_breadth** (258 ms) — 10-day advancer/decliner/avg-return table.
- **volume_anomalies** (263 ms) — top-20 volume-ratio anomaly table.
- **list_views** (2 873 ms) — the slowest surface, but still ~9.6 % of budget.
  It enumerates every DuckDB view and runs a row-count per view (42 lines of
  JSON output). This is expected: it is a meta/schema surface, not a hot
  query path. Flagged for awareness, not action.

### FastAPI `/api/health` (budget < 50 ms)

1.27 ms median via Starlette `TestClient` (no socket — matches the smoke-test
approach). 39x headroom under the 50 ms CORS-preflight baseline.

### CLI `rsrs --top 10` (budget <= 30 000 ms)

865 ms median as a subprocess (includes Python interpreter startup +
import). Exit code 0, 12 stdout lines. Subprocess overhead dominates the
measured latency; the underlying service call is the same one timed in
`mcp.tool:rsrs_ranking` above.

---

## Verdict

**PASS.** All declared performance budgets are met with substantial headroom
on real local data. The gate-check CONCERN "Performance within budget" is
resolved by this baseline. The harness is reproducible — re-run
`python tools/perf/profile_baseline.py` to regenerate.

---

## Sign-off

- Profile executed: 2026-06-12
- Surfaces covered: 6 MCP tools, FastAPI health, CLI rsrs (8 total)
- Reproducibility: deterministic inputs; 5-run median post-warmup
- Local-only invariant: confirmed via composition-root call-chain read

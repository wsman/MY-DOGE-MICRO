# Operations Runbook

Operator procedures for running, backing up, tuning, and troubleshooting the
MY-DOGE-MICRO local-first quantitative decision-support platform. Every claim
cites a source file:line or CDD section the operator can open to confirm.

## Audience & posture

This is a **local-first, single-operator** system:

- **One operator, one machine.** There is no remote cluster, no multi-tenant
  concurrency, and no shared database server. The target platform is Windows
  (cross-platform shell scripts exist for MCP startup); local-first data
  directories are a first-class constraint (`standards/technical-preferences.md`).
- **Single writer per market.** The scan pipeline assumes one in-flight scan per
  market; SQLite is opened in its default journal mode with no `WAL` and no
  `busy_timeout` (`design/cdd/market-data-storage.md` §9.3). See
  [Concurrency & single-writer contract](#concurrency--single-writer-contract).
- **Secrets live in the environment, not in the repo.** `DEEPSEEK_API_KEY` is
  read from the process environment (S002-013, `src/macro/config.py:185-200`).
  `models_config.json` ships only a placeholder sentinel.

## Table of contents

- [Port reference](#port-reference)
- [Backup & restore](#backup--restore)
- [Retention tuning](#retention-tuning)
- [DeepSeek API key environment verification](#deepseek-api-key-environment-verification)
- [DuckDB view refresh](#duckdb-view-refresh)
- [Resolved: `vw_rsrs_ranking` sign convention (S003-005)](#resolved-vw_rsrs_ranking-sign-convention-s003-005)
- [Troubleshooting](#troubleshooting)
- [Logging & observability](#logging--observability)
- [Concurrency & single-writer contract](#concurrency--single-writer-contract)

---

## Port reference

| Port  | Process / surface                                   | Source |
|-------|-----------------------------------------------------|--------|
| 8901  | FastAPI app (Tauri sidecar) — `src/api/main.py`     | `src/api/main.py:120` (`uvicorn.run(app, host="127.0.0.1", port=8901)`) |
| 8902  | MCP SSE transport — `doge_mcp.py`                   | `src/doge/interfaces/mcp/server.py` (`--port` default 8902); `MCPConfig.sse_port`, `src/doge/config/settings.py:134` |
| 7709  | TDX **CN** quote server                             | `TDXConfig.cn_port`, `src/doge/config/settings.py:81` |
| 7727  | TDX **US** quote server                             | `TDXConfig.us_port`, `src/doge/config/settings.py:82` |

All FastAPI/MCP HTTP surfaces bind to `127.0.0.1` only — they are not reachable
from other hosts. TDX ports 7709/7727 are outbound connections to the configured
TDX servers (`TDXConfig.cn_servers` / `us_servers`, `settings.py:73-80`).

---

## Backup & restore

### What to back up

All persisted state lives under `DOGE_DB_DIR` (default `<repo>/data`; override
via `DOGE_DB_DIR`, `DBConfig.dir`, `src/doge/config/settings.py:55`). Back up
**all** of the following on a regular schedule:

| Artifact | Path (under `DOGE_DB_DIR` unless noted) | Purpose |
|----------|------------------------------------------|---------|
| CN SQLite DB | `market_data_cn.db` (`DBConfig.cn_db`) | A-share OHLCV — the primary write target |
| US SQLite DB | `market_data_us.db` (`DBConfig.us_db`) | US equity OHLCV |
| Research insights DB | `research_insights.db` (`DBConfig.research_db`) | Notes / insights / knowledge graph (`design/cdd/research-insight-knowledge-base.md`) |
| DuckDB analytical DB | `market.duckdb` (`DBConfig.duckdb`) | Attached analytical views (regenerable from the SQLite DBs + `views.sql`) |
| DuckDB view definitions | `views.sql` (`DBConfig.views_sql`) | The view SQL itself (tracked in git, but include in cold backup for completeness) |
| Macro strategy reports | `macro_report/` (repo-relative) | LLM-generated macro reports, `src/macro/strategist.py:132-136` |
| Micro momentum reports | `micro_report/` (repo-relative) | `Top200_Momentum_{CN,US}_*.csv` outputs, `src/micro/momentum_scanner.py:350-371` |
| AI-analysis reports | `ai_report/` (`Settings.report_dir`, `settings.py:148-149`) | `market_overview_*.md`, `anomaly_detection_*.md` |
| Operator settings | `user_settings.json` (repo root) | Per-operator UI/runtime settings |
| Model profiles | `models_config.json` (repo root) | DeepSeek/LM Studio profile wiring (contains only the placeholder — no real key to back up) |

> **Note on `research_report/`:** earlier recon referenced a `research_report/`
> directory. As of this writing the on-disk report directories are
> `ai_report/`, `macro_report/`, and `micro_report/` only. `research_report/`
> does **not** exist; research content persists inside `research_insights.db`.

### Backup procedure

Two strategies, in order of preference:

**1. Cold file copy (simplest, recommended for single-operator).** Stop all
writers (MCP server, FastAPI, GUI, CLI scans), then copy the directory tree
while no process holds the SQLite files open:

```bash
# Windows / bash — stop consumers first, then:
cp -r data/ "data_backup_$(date +%Y%m%d)/"
cp -r macro_report/ micro_report/ ai_report/ "reports_backup_$(date +%Y%m%d)/"
cp user_settings.json models_config.json "reports_backup_$(date +%Y%m%d)/"
```

A cold copy of a quiescent SQLite file is a consistent snapshot. Do **not**
copy `market_data_cn.db` while a scan is mid-write — you may capture a
half-applied transaction.

**2. SQLite online `.backup` (if you cannot stop writers).** Use the SQLite
`.backup` CLI, which coordinates with the live writer and produces a
non-corrupt destination even under concurrency:

```bash
sqlite3 data/market_data_cn.db ".backup data_backup_cn.db"
sqlite3 data/market_data_us.db ".backup data_backup_us.db"
sqlite3 data/research_insights.db ".backup data_backup_research.db"
```

DuckDB (`market.duckdb`) does not need `.backup` — it is fully regenerable
from the three SQLite DBs plus `data/views.sql` via
[DuckDB view refresh](#duckdb-view-refresh). Include it in cold copies for
convenience only.

### Restore procedure

1. **Stop all writers** — kill the MCP server, FastAPI (`:8901`), and any
   desktop GUI / CLI scan. Confirm no process holds the DB files:
   ```bash
   # data/.mcp_server.pid should be empty or absent after a clean stop
   # (see PID orphan detection in Logging & observability)
   ```
2. **Replace the artifacts** in `DOGE_DB_DIR` with the backup copies.
3. **Refresh the DuckDB views** — restored SQLite DBs may carry a different
   max-date than the cached `market.duckdb` views expect. Run the manual
   refresh (see [DuckDB view refresh](#duckdb-view-refresh)) before serving
   reads.
4. **Restart consumers** and run `mcp__doge-db__list_views` to confirm every
   view has a non-null row count (a null/empty view signals a partial refresh
   failure).

---

## Retention tuning

### Shipped behavior (S002-007)

`DOGE_RETENTION_DAYS` controls the per-ticker destructive prune applied on
**every** OHLCV write:

- **Default: `730` days.** `MarketConfig.retention_days` reads
  `DOGE_RETENTION_DAYS` via `_env_int(..., 730)`
  (`src/doge/config/settings.py:112`).
- **Safe minimum is `730`.** The widest analytical-view window is
  `vw_market_breadth_cn` at `INTERVAL 730 DAYS` (`data/views.sql:33`). A
  `DOGE_RETENTION_DAYS` below 730 silently truncates breadth scans because
  the destructive `DELETE` runs before the view is queried. The guard
  `tests/migration/test_retention_view_window_safety.py` asserts
  `max(INTERVAL N DAYS) <= retention_days` (`design/cdd/market-data-storage.md`
  §8, AC).
- **Destructive.** Each write computes `cutoff = now - retention_days` and runs
  `DELETE FROM stock_prices WHERE ticker = ? AND date < ?` per ticker
  (`src/micro/database.py:166,187-188`). There is no undo.

```bash
# Inspect the effective value (after any env override):
DOGE_RETENTION_DAYS=730   # default; set higher to keep more history
```

### Warm-up caveat — no instant backfill

Raising `DOGE_RETENTION_DAYS` does **not** backfill history. The TDX ingest
path is capped at `TDXReader.MAX_DAYS = 120` bars per fetch
(`src/micro/tdx_loader.py:64`, `trim_to_recent` at `:135-137`). Increasing
retention to 730 therefore yields only ~120 days immediately; the remaining
history accumulates **gradually** over subsequent daily scans (one new bar
per ticker per scan). This is documented as a high-risk inconsistency in
`design/cdd/market-data-storage.md` §5 (Edge Cases) and §7 (Configuration
Knobs, `MAX_DAYS` row).

Operators who need deeper history immediately must perform a manual backfill
out-of-band (e.g. a yfinance history pull); note that any single fetch longer
than `retention_days` is itself subject to the destructive prune.

### DB-size note (180 → 730)

Raising retention from the legacy 180-day default to the shipped 730-day
default grows the on-disk size of `market_data_cn.db` (and to a lesser degree
`market_data_us.db`) roughly **4×**, since each ticker now retains ~4× the
rows. The exact delta is dataset-dependent (ticker count × bars-per-ticker).
Sprint-002 risk register R1 flagged this as **unmeasured**; treat 4× as an
order-of-magnitude planning estimate and measure on your live DB before
committing disk budget. A quick measurement:

```bash
# Approximate row count and on-disk size of the CN DB:
sqlite3 data/market_data_cn.db "SELECT COUNT(*) FROM stock_prices;"
ls -lh data/market_data_cn.db
```

---

## DeepSeek API key environment verification

### Shipped behavior (S002-013)

`DEEPSEEK_API_KEY` is the **PRIMARY** key source (`src/macro/config.py:185-187`):

```python
env_api_key = os.environ.get("DEEPSEEK_API_KEY")
if env_api_key:
    self.api_key = env_api_key
```

`models_config.json` ships only the `REPLACE_WITH_DEEPSEEK_API_KEY` placeholder
sentinel in every profile's `api_key` field (`models_config.json:7,13`). The
sentinel **must not** reach `OpenAI(...)`: if the env var is unset and the
on-disk value is the placeholder, `None`, or empty, `MacroConfig` raises a
typed `RuntimeError` with an actionable remediation message
(`src/macro/config.py:183,193-200`) instead of the legacy print-and-continue.

The key is passed **only** to `OpenAI(api_key=..., base_url=...)` and is never
logged (`design/cdd/macro-strategy-engine.md` §3.3, §9.6). The local FastAPI
`GET /api/config` additionally drops `api_key` from its HTTP response
(`design/cdd/macro-strategy-engine.md` §4.2).

> **History note.** A forensic audit of the repository confirmed that no real
> DeepSeek key was ever committed to git history. `models_config.json` has been
> gitignored since the initial commit; only `models_config.template.json` was
> tracked, and it always contained a placeholder (`YOUR_API_KEY_HERE`, later
> `REPLACE_WITH_DEEPSEEK_API_KEY`). Therefore no key rotation or history rewrite
> is required. Operators only need to export a valid `DEEPSEEK_API_KEY` and
> verify that macro report generation works.

### Environment verification procedure

```bash
# 1. SET the key in the environment of every consumer:
#    (MCP server, FastAPI app, GUI, CLI — each reads DEEPSEEK_API_KEY at startup)
export DEEPSEEK_API_KEY="<your-key>"

# 2. RESTART every consumer so the env value is picked up. MacroConfig
#    reads the env once in __post_init__ (_apply_runtime_overrides); a live
#    process will keep the previous value until restarted.

# 3. VERIFY a consumer produces a report end-to-end. The macro CLI exits 1
#    on any failure (src/macro/cli.py:82,87), so a 0 exit + a written report
#    in macro_report/ is the success signal:
python -m src.macro.cli && ls -t macro_report/ | head -1
```

A successful `python -m src.macro.cli` writes a new `macro_report/<ts>_macro.md`
(`src/macro/strategist.py:132-136`). If the CLI prints the RuntimeError
remediation message and exits 1, the env var was not visible to the process —
confirm the export in the **same shell/session** that runs the consumer.

### Never log the key

Do not add the key to log statements, error envelopes, or commit messages. The
API error envelope (`{"error": {"code", "message"}}`, S002-009) is built to
never leak `str(e)` (`src/api/routers/data.py:108-112`). If you debug a key
problem, redact the key before sharing logs.

---

## DuckDB view refresh

### How & when views refresh

The DuckDB analytical layer attaches the two SQLite DBs read-only and exposes
analytical views defined in `data/views.sql` (enumerated in
`design/cdd/market-data-storage.md` §3.6, §4.4). Views refresh:

- **Automatically after each CN/US sync** via `market_scanner._refresh_duckdb_views()`
  (`src/micro/market_scanner.py:44-53`), invoked at `:136`, `:168`, `:207`,
  `:238`. Each scan re-runs the full `views.sql`.
- **Best-effort by the scan router** at `src/api/routers/scan.py:208-215`,
  where a refresh failure is swallowed (non-fatal).

The refresh implementation is `DuckDBConnection.refresh_views`
(`src/doge/infrastructure/database/duckdb.py:58-83`), which splits `views.sql`
on `;` and executes each non-comment statement.

### Silent partial-failure risk

`refresh_views` swallows per-statement failures
(`src/doge/infrastructure/database/duckdb.py:74-80`):

```python
for stmt in sql.split(";"):
    ...
    try:
        con.execute(stmt)
    except Exception:
        pass  # Best-effort; individual views may fail
```

A **partial refresh is indistinguishable from a full refresh** — one failing
view leaves the others freshly built and emits no error. An operator sees no
warning if, say, `vw_volume_anomalies_cn` fails while `vw_market_breadth_cn`
succeeds.

### Manual refresh

To force a refresh outside a scan (e.g. after a restore or a `views.sql`
edit), connect with write access and re-run the SQL using the same code path
the scanner uses:

```python
from doge.infrastructure.database.duckdb import DuckDBConnection
DuckDBConnection(read_only=False).refresh_views()
```

### Verify a refresh

Use the `mcp__doge-db__list_views` MCP tool, which enumerates every view with
its row count and columns (`src/doge/interfaces/mcp/tools/views.py`). After a refresh, every
view should report a non-null, non-zero row count (for markets that have data).
A view showing `"rows": null` means its `COUNT(*)` failed — investigate that
view's SQL against the underlying SQLite table.

---

## Resolved: `vw_rsrs_ranking` sign convention (S003-005)

The DuckDB RSRS ranking views (`vw_rsrs_ranking_cn`, `vw_rsrs_ranking_us`)
previously computed the regression slope with the time index ordered newest
first (`ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) AS rn`,
rn=1=newest), which **inverted the RSRS sign for every monotonic series**
relative to the canonical Python path. The MCP `rsrs_ranking` tool and the
`doge rsrs` CLI (which read the view) inherited the inversion. **This is now
fixed.**

**Fix (S003-005).** The two RSRS views now regress on an ascending time index
`ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date ASC) AS rn_asc`
(rn_asc=1=oldest), matching the canonical Python
`MomentumRanker.calculate_rsrs` convention (`x = np.arange(len(y))` oldest ->
newest, `src/micro/momentum_scanner.py:95-116`). The downstream liquidity and
60-day-change CTEs keep the original DESC `rn` (rn=1=newest) so their
semantics are unchanged — only the regression's time index was corrected. A
perfectly increasing 18-bar window now yields RSRS = **+1.0** from both the
view and Python.

**Version-controlled DDL.** The view DDL was previously gitignored at
`data/views.sql` (untracked, owned by the market-data-storage refresh path).
It now ships under version control at the canonical, package-relative path:

```
src/doge/infrastructure/database/views.sql
```

A mirror copy remains at `data/views.sql` for backward compatibility with the
`duckdb data/market.duckdb < data/views.sql` CLI invocation. The refresh path
resolves the DDL via `DBConfig.resolved_views_sql()` (tracked-first,
data-dir fallback), so the version-controlled copy is always preferred when
present. Both the clean-arch refresh (`DuckDBConnection.refresh_views`) and
the legacy `ai_analysis.run_views_sql` loader now strip SQL comments before
statement-splitting (the tracked DDL's header prose contains semicolons that
previously broke the naive `split(';')`).

**Verification.** Cross-implementation parity holds: querying the live view
and `MomentumRanker.calculate_rsrs` on the same 18-bar window agrees to 1e-5
on both sign and magnitude for uptrend and downtrend tickers. Regression
guard: `tests/migration/test_rsrs_view_sign_convention.py`
(`test_perfectly_increasing_view_is_positive_one`) is now a hard assertion
(the strict xfail that previously pinned the inversion was removed).

**Operator guidance.** The MCP `rsrs_ranking` tool, the `doge rsrs` CLI, the
Top200 CSV, and the DuckDB view now all use the same canonical sign
convention. No workaround is required; the view output is sign-canonical.

---

## Troubleshooting

| Symptom | Expected cause | Fix | Source |
|---------|----------------|-----|--------|
| Scan / query returns stale data | DuckDB views were not refreshed after the last write | Run a manual refresh ([DuckDB view refresh](#duckdb-view-refresh)); verify with `mcp__doge-db__list_views` | `src/micro/market_scanner.py:44-53`; `duckdb.py:58-83` |
| `vw_market_breadth_cn` returns fewer rows than expected / breadth scan looks truncated | `DOGE_RETENTION_DAYS` < 730 (below the 730-day view window) — destructive prune cut rows the view expects | Set `DOGE_RETENTION_DAYS=730` (or higher) and restart; the guard `tests/migration/test_retention_view_window_safety.py` enforces `max(INTERVAL N DAYS) <= retention_days` | `data/views.sql:33`; `design/cdd/market-data-storage.md` §9.2, §7 |
| `python -m src.macro.cli` prints a `RuntimeError` and exits 1 (`DEEPSEEK_API_KEY ... not set ... still carries the placeholder`) | `DEEPSEEK_API_KEY` env var unset/empty and `models_config.json` still has the placeholder | Set `DEEPSEEK_API_KEY=<key>` in the consumer's environment and restart; see [DeepSeek API key environment verification](#deepseek-api-key-environment-verification) | `src/macro/config.py:193-200`; `src/macro/cli.py:79-87` |
| Macro run returns `None` / "无法获取市场数据" (exits 1) | Network failure fetching market data (yfinance/TDX upstream), not a key problem | Check network reachability to the data source; `data_loader` returned `None` and the CLI exited at `src/macro/cli.py:82-87` | `src/macro/cli.py:82-87`; `design/cdd/macro-strategy-engine.md` §3.2 |
| `database is locked` during a scan | Two writers hit the same SQLite DB concurrently — no `WAL`, no `busy_timeout` is configured | Ensure only one scan per market runs at a time (the scan lock normally serializes this, `src/api/routers/scan.py:46,157`); stop the second writer and retry | `design/cdd/market-data-storage.md` §9.3, Open Question 6 |
| DuckDB `ATTACH ... AS cn/us` fails | `DOGE_CN_DB` / `DOGE_US_DB` paths do not sit alongside `DOGE_DUCKDB_PATH` under the resolved `DOGE_DB_DIR` — path mismatch between the DuckDB file and the SQLite files it attaches | Confirm all DB env vars resolve under the same `DOGE_DB_DIR`; `DBConfig` derives `cn_db`/`us_db`/`duckdb` from one `dir` (`__post_init__`), so mixing absolute overrides across the three breaks the attach | `src/doge/config/settings.py:62-67`; `design/cdd/runtime-configuration.md` §3.4 |
| MCP tool returns "timed out after 30s" | Tool execution exceeded `TOOL_TIMEOUT` (30 s) | Narrow the query (fewer tickers / smaller `days`); for sustained heavy queries, raise is governed by `MCPConfig.tool_timeout` (`src/doge/config/settings.py:131`) | `src/doge/interfaces/mcp/server.py:80,173,182` |
| SSE scan stream stuck on `running` after a dropped connection | (Resolved in S002-010) The scan now emits a terminal error event (`progress: -1`) and resets status to `idle` in `finally` | If you still observe a stuck `running`, the consumer predates S002-010 — restart the FastAPI app on the current build | `src/api/routers/scan.py:97-103` |
| API returns `{"error":{"code":"internal_error",...}}` | An unexpected exception reached the global handler; the envelope never leaks `str(e)` | Inspect `logs/app.log` server-side for the stack trace; the response message is deliberately generic | `src/api/routers/data.py:108-112`; S002-009 |

---

## Logging & observability

### Log file locations

| Log | Path | Writer | Rotation |
|-----|------|--------|----------|
| MCP server log | `logs/mcp_server.log` | `src/doge/interfaces/mcp/server.py` (root logger, `RotatingFileHandler`) | 10 MB × 5 backups |
| App / macro log | `logs/app.log` | `src/macro/utils.py:13-65` (`setup_logging`, `RotatingFileHandler`) | 10 MB × 5 backups |
| Generated reports | `macro_report/*.md`, `micro_report/*.csv`, `ai_report/*.md` | macro strategist / momentum scanner / ai_analysis | (not rotated — operator-managed) |

### Correlation IDs

Every MCP log line carries a `correlation_id` field
(`src/doge/interfaces/mcp/server.py`):

```
2026-06-12 10:14:02 [INFO] [a1b2c3d4] doge.mcp: list_views ok
```

The `correlation_id` is a `contextvars.ContextVar` defaulting to `-`. When
debugging a single request, grep for its correlation id to follow it across
log lines.

### PID orphan detection

The MCP server registers its PID in `data/.mcp_server.pid` on startup
(`src/doge/interfaces/mcp/server.py`) and removes it on clean shutdown. On
startup it scans the PID file and warns if it detects processes that are no
longer alive (`_detect_orphan_processes`). Detection
is **read-only** — it logs a warning; it does **not** kill orphans. If you see
the warning, manually stop the orphaned `doge_mcp.py` process and delete
stale lines from `data/.mcp_server.pid`.

### Health & metrics endpoints (SSE mode)

When the MCP server runs in SSE transport (`--transport sse`, default port
8902), it exposes two custom routes:

- `GET /health` (`src/doge/interfaces/mcp/server.py`) — runs `SELECT 1` against DuckDB;
  returns `{"status":"ok"}` (200) or `{"status":"error","detail":...}` (503).
- `GET /metrics` (`src/doge/interfaces/mcp/server.py`) — returns a Prometheus-style
  exposition of `mcp_requests_total{tool=...}` and
  `mcp_request_duration_seconds_{sum,count}` from the in-memory counters.

These are SSE-mode only (`@mcp.custom_route`); they are not available on the
stdio transport.

---

## Concurrency & single-writer contract

The platform is built for a single operator and assumes a **single writer per
market**:

- **Per-market scan locks.** `src/api/routers/scan.py:46` holds one
  `threading.Lock` per market (`_scan_locks = {"cn": ..., "us": ...}`). A
  second scan for an already-running market is rejected with HTTP 409
  (`src/api/routers/scan.py:157`). The lock is released and status reset to
  `idle` in a `finally` block (`:101-103`).
- **No WAL, no `busy_timeout`.** SQLite runs in its default journal mode with
  no busy timeout. Two concurrent writers to the same DB receive
  `database is locked` immediately (`design/cdd/market-data-storage.md` §9.3,
  Open Question 6). Storage performs **no retries** on this error
  (`design/cdd/market-data-storage.md` §9.5).
- **Single-process uvicorn.** The FastAPI app assumes one uvicorn worker
  (`src/api/main.py:120`). Scaling to multiple workers would multiply writers
  against the same SQLite files and is **not supported** by the current
  contract.

**Operator rule:** never run two scans for the same market simultaneously,
and never run the desktop GUI scan and the CLI/API scan against the same DB at
the same time. The scan lock protects the API path; a GUI- or CLI-initiated
scan bypasses it and can collide with an in-flight API scan.

---

## Cross-references

- `docs/MCP_SERVER.md` — MCP tool catalog, SSE deployment, `/health`/`/metrics`.
- `docs/GETTING_STARTED.md` — install + first-run (env-var table, entrypoints).
- `design/cdd/market-data-storage.md` — storage schema, retention, concurrency
  model (§9), DuckDB view enumeration (§4.4).
- `design/cdd/macro-strategy-engine.md` — macro config, key handling (§3.1,
  §9.6), LLM client (§3.3).
- `design/cdd/runtime-configuration.md` — `DBConfig` env overrides (§3.4),
  singleton lifecycle (§3.9).
- `docs/architecture/adr-0002-centralized-configuration.md` — env-config as
  the single source of truth.
- `docs/architecture/adr-0003-storage-repository-contract.md` — storage /
  retention contract.
- `docs/architecture/adr-0005-llm-client-strategy.md` — LLM client + key
  handling decisions.

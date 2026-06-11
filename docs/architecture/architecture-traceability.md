# Architecture Traceability & Review

> **Manifest Version**: 2026-06-12
> **Reviewer**: Independent architecture reviewer (fresh context — did not author these ADRs/CDDs)
> **Scope**: ADR-0001..ADR-0008 + 12 module CDDs + module-index + product-concept
> **Method**: `/architecture-review` discipline — read every ADR and CDD, cross-checked ports/paths/RSRS/versions/statuses, then mapped each load-bearing requirement to a TR-ID in `tr-registry.yaml`.
> **Do NOT** edit the ADRs or CDDs based on this review without routing through `/architecture-decision` (Proposed→Accepted) or a CDD authoring pass.

---

## 1. Verdict

The architecture is **internally coherent and largely self-consistent** for an early-stage brownfield reverse-documentation. Every module has a traceable governing ADR (or an explicit "no new ADR — this is a product/algorithm decision" rationale), the pinned stack versions agree across `requirements.txt`, `docs/reference/python/VERSION.md`, every ADR's compatibility table, and `standards/technical-preferences.md`, and the eight analytical views, the canonical RSRS formula, and the five `DOGE_*` env vars are each named identically wherever they appear.

The review surfaces **five real findings**, two of them **HIGH** severity:

- **FINDING-1 (HIGH): ADR lifecycle violation** — five of the eight ADRs are still `Proposed`, yet they are the load-bearing governance for CDDs whose acceptance criteria and integration requirements cite them as if binding. Per `docs/CLAUDE.md`, *stories referencing a `Proposed` ADR are auto-blocked*, and the CDDs (notably `macro-strategy-engine.md §8`) already self-flag this. This is a control-plane gap, not a design gap.
- **FINDING-2 (HIGH): Module #6 (AI Industry Analysis) has no CDD at all** — the module-index lists its Design Doc as `—`, yet `src/micro/industry_analyzer.py` is the only place outside Module #4 that constructs a DeepSeek LLM client and the bridge from Module #5's CSV to a research-DB-archived report. Two placeholder TRs (TR-020, TR-021) carry the gap; the bidirectional dependency that `research-insight-knowledge-base.md §6` explicitly defers ("when Module #6's CDD is authored, it must add #7…") cannot be closed without it.
- **FINDING-3 (MEDIUM): RSRS formula has three implementations with three divergent zero-slope sign conventions** that only agree because a zero-variance guard masks the difference — documented honestly in `micro-momentum-scanner.md §4.1` and `macro-strategy-engine.md §4.3`, but the divergence (macro local copy returns `nan` on flat series; canonical returns `0.0`) is a **live BUG-class drift** the CDDs themselves flag as open.
- **FINDING-4 (MEDIUM): Port-naming drift** — ADR-0001 uses non-prefixed names (`StockRepository`, `MarketDataSource`, `TickerMetadataSource`/`Cache`); source ABCs use `I`-prefixed names (`IStockRepository`, `IMarketDataSource`, `ITickerNameCache`). `clean-architecture-migration.md §4.1` flags this as OQ-2 but it is unresolved.
- **FINDING-5 (LOW): Two registries referenced by CDDs (`entities.yaml`, a constants registry) do not exist** — every Foundation/Core CDD proposes `entities.yaml` entries and explicitly notes the file is absent and that writing it is a separate BLOCKING approval step. This is expected at this stage but is recorded so the next `/architecture-decision` Phase-5 pass has a known backlog.

No contradictions between Accepted ADRs were found. No version skew was found. No module is missing traceability.

---

## 2. Architecture As-Built

MY-DOGE-MICRO is a **local-first quantitative investment decision-support platform**. The current state is a **brownfield coexistence**: a working legacy tree (`src/micro`, `src/macro`, `src/api`, `src/ai_analysis`, `src/interface`, root `mcp_server.py`) runs alongside an in-progress clean-architecture target (`src/doge/{config,core,infrastructure,interfaces}`). Both entrypoints are live and tested; the migration is incremental and brownfield per ADR-0001.

### 2.1 Layer model (target, from ADR-0001 + `clean-architecture-migration.md §3.2/§4.3`)

```
Presentation / Interface
   │  (PyQt6 desktop · Vue3 web · MCP clients · CLI · FastAPI HTTP)
   ▼
src/doge/interfaces/*      ── depends only on core.services + config
   ▼
src/doge/core/services/*   ── depends only on core.ports + core.domain
   ▼
src/doge/core/ports/*      ── abstract; stdlib + core.domain only
   ▲
   │  (implements ports)
src/doge/infrastructure/*  ── concrete adapters; may import drivers
   │
   ▼
SQLite (cn/us/research) · DuckDB (market.duckdb) · TDX/yfinance · caches
```

**Known deviation from the strict rule** (`clean-architecture-migration.md §3.2`, AC-9/OQ-5): the four view-backed services (`RankingService`, `BreadthService`, `AnomalyService`, `ViewService`) take a concrete `DuckDBConnection` adapter rather than a port. Only `StockService` depends on a true abstract port (`IStockRepository`). ADR-0001 permits this as an interim step; formal reconciliation is TR-041.

### 2.2 Port / service / adapter map

| Port (source ABC) | Canonical name (ADR-0001) | Adapter(s) | Implemented? |
|---|---|---|---|
| `IStockRepository` (`ports/repository.py`) | StockRepository | `DuckDBStockRepository` (`infrastructure/database/repositories.py`) | read paths; `save_prices`/`delete_older_than` proposed (TR-005) |
| `IReportRepository` (`ports/repository.py`) | ReportRepository (+ target split: NoteRepository) | `SQLiteReportRepository` | reports/notes/names; `delete_note` + 4 reads pending (TR-022) |
| `IMarketDataSource` (`ports/data_source.py`) | MarketDataSource | `YFinanceDataSource` (working), `TDXDataSource` (**stub** — raises NotImplementedError) | TR-011 |
| `ITickerNameCache` (`ports/cache.py`) | TickerMetadataSource *or* Cache (mutually-exclusive candidate names — OQ-2) | `JSONTickerNameCache` | implemented; name unresolved (TR-042) |
| *(proposed)* `ILLMClient` (`core/ports/llm_client.py`) | — | `DeepSeekAdapter` (target) | not yet extracted; strategist is the single LLM call site (TR-013) |

**Core services** (`src/doge/core/services/`): `StockService(IStockRepository)`, `RankingService`, `BreadthService`, `AnomalyService`, `ViewService` — the latter four constructed with `DuckDBConnection`.

### 2.3 The four ADR-governed cross-cutting decisions

1. **Storage access is exclusively through repository ports** (ADR-0003) — no `sqlite3`/`duckdb` import in any interface layer. The destructive `retention_days=180` and the swallowed write exception (`src/micro/database.py:152-153`) are tracked for remediation (TR-006).
2. **External data access is exclusively through `IMarketDataSource` adapters** (ADR-0004) — 8-column canonical frame, degrade-to-`None`, shared bounded retry (TR-009, TR-010).
3. **All LLM access is exclusively through the OpenAI-compatible SDK via one strategist** (ADR-0005) — DeepSeek default, secrets via env/config, degrade-to-`None`, no in-strategist retry (TR-013, TR-014).
4. **MCP is a single FastMCP server with dual transport (stdio primary, SSE secondary)** (ADR-0006) — six read-only tools, uniform 30s `_timed` timeout, `"Error: …"` string contract, zero-copy DuckDB reads (TR-025–TR-028).

---

## 3. ADR Status Inventory

| ADR | Title | Status | Appropriate? |
|---|---|---|---|
| 0001 | Brownfield Clean Architecture Migration | **Accepted** | Yes — foundational, no depending ADRs above it. |
| 0002 | Centralized Runtime Configuration | Proposed | **See FINDING-1** — `settings.py` is already implemented and consumed; `runtime-configuration.md` treats it as binding. Recommend promote to Accepted. |
| 0003 | Storage Repository Contract | Proposed | **See FINDING-1** — `market-data-storage.md §6` self-flags: "Status: Proposed as of 2026-06-11 — not yet binding." Recommend promote once `save_prices`/`StorageWriteError` land. |
| 0004 | Data Source Adapter Contract | Proposed | **See FINDING-1** — TDX adapter is a stub; yfinance adapter done. Acceptable as Proposed *until* TR-011 (TDX migration) completes; but the yfinance-half could be split out and Accepted now. |
| 0005 | LLM Client Strategy | Proposed | **See FINDING-1** — `macro-strategy-engine.md §8` explicitly notes this blocks stories. Recommend promote to Accepted (the strategy is frozen; only migration items remain). |
| 0006 | MCP Transport Strategy | **Accepted** | Yes — verified against installed SDK; 77 transport tests green. |
| 0007 | API Surface and CORS | Proposed | Appropriate as Proposed — the gating work (CORS hardening + error envelope) is genuinely open; ADR-0007 itself states this honestly. |
| 0008 | Vue Web Console Architecture | **Accepted** | Yes — reverse-documented, build-green. |

**Net**: 3 Accepted, 5 Proposed. Of the 5 Proposed, **0002 and 0005 are the most overstretched** — their governing modules ship working code and cite them as load-bearing.

---

## 4. Cross-ADR / Cross-CDD Consistency Checks (passed)

| Dimension | Finding |
|---|---|
| **Pinned versions** | FastAPI 0.123.8, Uvicorn 0.38.0, Pydantic 2.12.4, MCP 1.25.0, sse-starlette 3.0.3, DuckDB 1.4.4, yfinance 0.2.66, openai 1.62.0, pytest 9.0.1, pytest-asyncio 1.3.0 — identical in `requirements.txt`, `docs/reference/python/VERSION.md`, every ADR compatibility table, and `standards/technical-preferences.md`. **No skew.** |
| **DB paths / env vars** | The five `DOGE_*` env vars (DB_DIR, CN_DB, US_DB, RESEARCH_DB, DUCKDB_PATH) and their defaults are named identically in `runtime-configuration.md §3.4/§7.1`, `market-data-storage.md §3.1`, `data-sources.md §7`, `clean-architecture-migration.md §7`, and `docs/MCP_SERVER.md`. The legacy parallel reader at `src/ai_analysis/__init__.py:24-36` reads the same names with the same defaults (TR-039). **Consistent; dual-source is a known migration target, not a contradiction.** |
| **Eight DuckDB views** | The view set (`vw_daily_enriched_cn`, `vw_rsrs_ranking_cn/us`, `vw_market_breadth_cn/us`, `vw_volume_anomalies_cn`, `vw_cross_sectional_return_cn`, `temp_vol_check`) is enumerated identically in `market-data-storage.md §4.4`, ADR-0006, and `mcp-server.md`. |
| **RSRS formula & window** | `window=18`, range `[-1.0, 1.0]`, `R² × sign(slope)` via `scipy.stats.linregress` — identical in `micro-momentum-scanner.md §4.1` (canonical), `macro-strategy-engine.md §4.3` (local copy), `market-data-storage.md §4.4` (DuckDB view), and `runtime-configuration.md §3.6` (`rsrs_window=18` default). **Divergence is only in the guards/sign-convention — FINDING-3.** |
| **MCP tool set & timeout** | The six tools and `TOOL_TIMEOUT=30` appear identically in ADR-0006, `mcp-server.md`, and `clean-architecture-migration.md §3.3/§7`. |
| **Forbidden-pattern set** | `direct_sqlite_import_in_interface`, `direct_duckdb_connect_in_interface`, `sys_path_insert`, `_PROJECT_ROOT_recalculation`, `cross_layer_state_write` — listed identically in ADR-0001, `clean-architecture-migration.md §4.4`, and `runtime-configuration.md §6.5`. The `standards/technical-preferences.md` "Forbidden Patterns" section restates the first four at the project level. |
| **30s MCP latency budget** | Stated in `standards/technical-preferences.md`, ADR-0006, `runtime-configuration.md §3.7`, and `clean-architecture-migration.md §7`. **Consistent.** |

---

## 5. Module Traceability Coverage

All 12 modules have at least one TR. Module #6 is covered by **placeholder TRs** because its CDD does not exist (FINDING-2).

| # | Module | CDD | Governing ADR | TR-IDs |
|---|---|---|---|---|
| 1 | Runtime Configuration | runtime-configuration.md | ADR-0002, ADR-0001 | TR-001–TR-004 |
| 2 | Market Data Storage | market-data-storage.md | ADR-0003, ADR-0001 | TR-005–TR-008 |
| 3 | TDX/YFinance Data Sources | data-sources.md | ADR-0004, ADR-0001 | TR-009–TR-012 |
| 4 | Macro Strategy Engine | macro-strategy-engine.md | ADR-0005, ADR-0004 | TR-013–TR-016 |
| 5 | Micro Momentum Scanner | micro-momentum-scanner.md | ADR-0001 (algorithm; no new ADR) | TR-017–TR-019 |
| 6 | AI Industry Analysis | **(no CDD)** | ADR-0005 (LLM client) | TR-020, TR-021 *(placeholders)* |
| 7 | Research Insight Knowledge Base | research-insight-knowledge-base.md | ADR-0003, ADR-0001 | TR-022–TR-024 |
| 8 | MCP Server | mcp-server.md | ADR-0006, ADR-0003 | TR-025–TR-028 |
| 9 | FastAPI Service | fastapi-service.md | ADR-0007 | TR-029–TR-032 |
| 10 | PyQt Desktop Dashboard | pyqt-desktop-dashboard.md | ADR-0001 (no new ADR) | TR-033, TR-034 |
| 11 | Vue Web Console | vue-web-console.md | ADR-0008, ADR-0007 | TR-035–TR-037 |
| 12 | Clean Architecture Migration | clean-architecture-migration.md | ADR-0001 | TR-038–TR-042 |

**Total: 42 TRs.**

---

## 6. FINDINGS

Each finding lists severity, evidence, and recommended action. Severities: **HIGH** (blocks stories / governance gap), **MEDIUM** (real defect or drift, not blocking), **LOW** (housekeeping / expected-at-stage).

### FINDING-1 — HIGH — ADR lifecycle: five Proposed ADRs are load-bearing for their CDDs

**Evidence**: ADR-0002, 0003, 0004, 0005, 0007 are `Proposed`. `docs/CLAUDE.md` ADR lifecycle rule: *"stories referencing a Proposed ADR are auto-blocked."* `macro-strategy-engine.md §8` self-flags: *"ADR-0005 is currently Proposed… Blocks stories referencing this CDD."* `market-data-storage.md §8`: *"ADR-0003 is Accepted before any story references it."* Yet the CDD integration-requirements sections (§9) treat these ADRs as the authoritative record for transport, retry, offline fallback, etc.

**Impact**: The five modules' acceptance criteria cannot be satisfied (or stories cannot be created) until the ADRs move to Accepted. For 0002 and 0005 the underlying decisions are already frozen and the code ships — the Proposed status is overdue.

**Recommended action**: Promote **ADR-0002** and **ADR-0005** to Accepted (decisions are frozen; only migration items remain). Promote **ADR-0003** once `save_prices` + `StorageWriteError` + `DOGE_RETENTION_DAYS` land (TR-006). Split **ADR-0004** — Accept the yfinance-adapter half now, leave the TDX-migration half Proposed until TR-011 completes. Leave **ADR-0007** Proposed (its gating work — CORS hardening + error envelope — is genuinely open, and ADR-0007 itself states this honestly).

### FINDING-2 — HIGH — Module #6 (AI Industry Analysis) has no CDD

**Evidence**: `module-index.md` row 6 lists Design Doc as `—`. `research-insight-knowledge-base.md §6` explicitly defers the bidirectional dependency: *"Module #6's CDD does not yet exist… TODO bidirectional: when Module #6's CDD is authored, it must add #7 research-insight-knowledge-base to its Depended-on-by list."* `micro-momentum-scanner.md §3.8` documents `industry_analyzer.py` (constructs a `DeepSeekStrategist`, calls `chat.completions.create` at `industry_analyzer.py:38-39,329-336`, reads Top-200 CSVs, archives to research DB) but notes ownership reconciliation is open Phase-5 work.

**Impact**: The bridge between Module #5's CSV output and the research-DB-archived industry report has no formal contract, no acceptance criteria, no traceability beyond two placeholder TRs. The macro↔micro circular dependency flagged in `docs/MODULARIZATION_PLAN.md:23` and `module-index.md §Circular Dependencies` cannot be resolved without it.

**Recommended action**: Author `design/cdd/ai-industry-analysis.md` covering `src/micro/industry_analyzer.py`: the yfinance `.info` metadata calibration + cache, the DeepSeek industry-chain prompt, the report-archive path, the RSRS interpretation thresholds (>0.8 HOT / <0.3 speculative, currently hardcoded in prompt), the proxy env-var mutation (`HTTP_PROXY`/`HTTPS_PROXY` at `industry_analyzer.py:48-51`), and the bidirectional dependency on #7.

### FINDING-3 — MEDIUM — RSRS has three implementations with divergent zero-slope sign conventions (live BUG-class drift)

**Evidence**: `micro-momentum-scanner.md §4.1` sign-convention note + Open Question 11 documents three divergent `sign` definitions: (a) Python scalar `1.0 if float(slope) > 0 else -1.0` (zero → **−1**); (b) Python vectorized `np.sign(slope)` (zero → **0**); (c) DuckDB SQL view `CASE WHEN COALESCE(REGR_SLOPE(...),0) >= 0 THEN 1 ELSE -1` (zero → **+1**). They only agree because the zero-variance guard (`np.var(y) ≤ 1e-10`) forces `r_sq=0` whenever slope can be exactly zero. `macro-strategy-engine.md §4.3` adds: the macro local copy (`data_loader.calculate_rsrs`, `data_loader.py:182-193`) has **neither** the flat-variance guard **nor** the NaN guard, so on a flat/zero-variance series it returns `nan` while the canonical Module #5 copy returns `0.0`.

**Impact**: Macro prompt dashboard can embed `nan` RSRS values where the momentum scanner would emit `0.0`, producing inconsistent risk framing between the macro report and the Top-200 CSV. The divergence is masked at the unit-test level because the tests probe the canonical copy, not the macro local copy.

**Recommended action**: Either (a) make `data_loader.calculate_rsrs` delegate to `momentum_scanner.calculate_rsrs`, or (b) replicate both guards (`momentum_scanner.py:64-65` + `:76`). This is gated on the shared-formula registry stance (`macro-strategy-engine.md §4.7`) and is captured as TR-016. Reconcile the three zero-slope sign conventions (OQ-11) at the same time.

### FINDING-4 — MEDIUM — Port-naming drift (I-prefix + competing cache-port names)

**Evidence**: ADR-0001 lists canonical port names without the `I` prefix (`StockRepository`, `ReportRepository`, `NoteRepository`, `MarketDataSource`); source ABCs use `I`-prefixed names (`IStockRepository`, `IReportRepository`, `IMarketDataSource`). Separately, ADR-0001 references **two** candidate names for the same cache adapter column — `TickerMetadataSource` and `Cache` — which `clean-architecture-migration.md §4.1` clarifies are *"mutually-exclusive candidate names for the same source class, not two separate ports."* The source class is `ITickerNameCache`. ADR-0001 also mentions a `TickerMetadataSource` port separately (for `industry_analyzer.py` `.info` calls) — adding genuine ambiguity.

**Impact**: Story authors and registry writers cannot tell which name is canonical. `research-insight-knowledge-base.md` and `clean-architecture-migration.md` both flag this (OQ-2).

**Recommended action**: Resolve at Phase-5 registry approval (TR-042): either alias-map the registry entries or rename the source ABCs. Decide whether `TickerMetadataSource` is a *separate* port (for `.info` metadata) from `Cache`/`ITickerNameCache` (for name lookup) — the CDDs are inconsistent on this.

### FINDING-5 — LOW — `entities.yaml` and a constants registry do not exist; every CDD proposes entries for them

**Evidence**: `docs/registry/` contains only `architecture.yaml` (cross-ADR stances, still a stub — no real entries). Every Foundation/Core CDD has a §4.7 "Registry proposals" section that proposes `entities.yaml` entries (ports, adapters, DB tables, env vars, RSRS knobs) and explicitly notes *"entities.yaml does not exist"* (e.g. `data-sources.md §4.5`, `micro-momentum-scanner.md §4.7`, `research-insight-knowledge-base.md §4.7`). The `architecture.yaml` header comment itself scopes it to cross-ADR stances only, so the value-constant proposals have no home.

**Impact**: No defect today — the CDDs are correctly deferring the writes to a separate BLOCKING approval step (per the assignment brief). But it is a known backlog: registry authoring must happen before `/create-stories` can embed architectural constraints in stories.

**Recommended action**: At the next `/architecture-decision` Phase-5 pass, (a) populate `docs/registry/architecture.yaml` with the cross-ADR stances already enumerated in CDD §4.7(a) sections, and (b) decide whether to create `docs/registry/entities.yaml` (constants) — possibly via its own ADR (the CDDs suggest a registry-design ADR is warranted first).

### Additional observations (not elevated to findings)

- **`docs/MCP_SERVER.md` env-var table omits `DOGE_DUCKDB_PATH`** — `runtime-configuration.md §9 #9` flags this; advisory only.
- **`docs/registry/architecture.yaml` is a stub** (all sections empty arrays) despite 8 ADRs existing — expected, since `/architecture-decision` Phase-5 has not run. The cross-ADR stances to populate it are already enumerated in the CDDs' §4.7 sections.
- **The `micro_report/` vs project-root CSV path drift** (`micro-momentum-scanner.md §4.2`) is documented as default-discovery-only and bypassable via explicit `run_analysis(cn_path=..., us_path=...)` — not a contradiction, just a UX wart.
- **`stock_notes` table is not created by `initialize_system_dbs()`** (`market-data-storage.md §3.4`, `research-insight-knowledge-base.md §9 #1`) — the live table exists from out-of-band creation; this is a known migration gap (TR-024's underlying persistence is sound, but cold-start does not bootstrap it).

---

## 7. Proposed ADRs Needing Ratification

These are decisions the CDDs implicitly assume are made but that do **not** have an ADR yet (or are buried as "open questions"). They should become Proposed ADRs (and then Accepted) before stories that depend on them are created.

1. **Registry-design ADR** — whether to create `docs/registry/entities.yaml` (a constants registry) and what its schema is. Every CDD §4.7 blocks on this. (FINDING-5)
2. **Retention / view-window consistency decision** — `retention_days=180` vs `MAX_DAYS=120` vs view windows (730/365/180). `market-data-storage.md §9 #1` documents that the 180-day retention is already shorter than the 730-day `vw_market_breadth_cn` window (silent breadth truncation). This needs an explicit decision (raise retention to ≥730, or shorten the view), not just an open question. Related to TR-006.
3. **Cache-port vs metadata-port split decision** — is `TickerMetadataSource` (for yfinance `.info`) a separate port from `Cache`/`ITickerNameCache` (for name lookup)? FINDING-4 / clean-architecture-migration OQ-2.
4. **View-service port-injection decision** — convert the four `DuckDBConnection`-backed services to ports (`IMarketViewRepository`) or formally amend ADR-0001 to permit adapter-injection for read-only view services. TR-041 / OQ-5.
5. **RSRS sign-convention unification** — a small product/algorithm decision (unify `sign` across Python scalar, Python vectorized, DuckDB SQL) that should be recorded so the masked-by-guard equivalence is intentional, not accidental. FINDING-3 / micro-momentum-scanner OQ-11.

---

## 8. Related Artifacts

- `docs/architecture/tr-registry.yaml` — the 42 TRs backing this review (written in the same pass).
- `docs/architecture/control-manifest.md` — the control-plane reference (quality gates, BLOCKING vs ADVISORY rules, ADR lifecycle, registry-write policy, verification commands) written in the same pass.
- `docs/registry/architecture.yaml` — the (stub) ADR-stance registry, to be populated at the next Phase-5 pass.
- `docs/CLAUDE.md` (Docs Directory section) — defines the ADR lifecycle and TR-registry contract this review honors.

*Reviewed 2026-06-12 against the working tree on branch `cdd-adoption-2026-06-11`.*

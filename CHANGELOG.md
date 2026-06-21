# Changelog

All notable changes to **MY-DOGE-MICRO** are recorded here.

## v0.2.1 — Metadata Port Alignment (2026-06-14)

Patch release that folds the post-`v0.2.0` architecture-hygiene tail into the
Release baseline and aligns package metadata with the git tag.

### Highlights
- **`fetch_names.py` metadata-port migration** — `src/ai_analysis/fetch_names.py`
  `fetch_batch_yfinance` now delegates to `ITickerMetadataSource` via
  `build_metadata_source()` instead of calling `yfinance.Ticker(...).info`
  directly (S006-006). A regression test guards the port contract.
- **Package version alignment** — `pyproject.toml` version bumped to `0.2.1`
  so the installed package version matches the git release tag.

### Verification
- `python -m pytest -q` → **617 passed, 5 skipped, 0 failed**
- `cd web && npm test` → **70 passed**
- `cd web && npm run build` → **green**
- `python src/cli.py demo --market cn --top 3` → exits 0 without `DEEPSEEK_API_KEY`
- §6 layer gate → **ZERO hits**

### Deferred
- `ADR-0007 path 1a` auth + non-loopback CORS allow-list — remains conditionally
  deferred until the deployment model changes from loopback.

---

## v0.2.0 — First-Run Experience + Architecture Completion (2026-06-14)

Post-Release polish sprint on top of `v0.1.0`. Closes the deferred Wave-5
hygiene items, finishes the ADR-0009 metadata-port follow-on, and ships a
zero-config first-run demo so new operators can see value in under five minutes
without a `DEEPSEEK_API_KEY`.

### Highlights
- **`python src/cli.py demo`** — zero-config first-run demo using bundled
  `data/*.db`; prints RSRS top-N, market breadth, volume anomalies, and a sample
  stock query. No LLM API key required.
- **`YFinanceMetadataSource` adapter** — full implementation of
  `ITickerMetadataSource` with lazy `yfinance` import, `.SH`→`.SS` suffix remap,
  retry reuse, settings-backed defaults, and degraded `None` return.
- **`industry_analyzer.py` port migration** — off direct `yf.Ticker(...).info`
  and onto `build_metadata_source().get_metadata(...)` via the composition root;
  in-memory cache and `meta_cache.json` persistence preserved.
- **Wave-5 hygiene closed**
  - `sys.path` test-shim regression gate + cleanup of ~29 redundant shims
  - MCP error-text sanitization (absolute paths + credential patterns redacted)
  - `wmic` → PowerShell CIM migration for orphan-process detection

### Verification
- `python -m pytest -q` → **613 passed, 5 skipped, 0 failed**
- `cd web && npm test` → **70 passed**
- `cd web && npm run build` → **green**
- `python src/cli.py demo --market cn --top 3` → exits 0 without `DEEPSEEK_API_KEY`
- §6 layer-rule grep gate → **ZERO hits**

### Deferred
- `S006-006` `fetch_names.py` optional metadata-port migration (Should Have).
- `ADR-0007 path 1a` auth + non-loopback CORS — conditionally deferred until
  deployment model changes from loopback.

---

## v0.1.0 — Release-Ready v1 (2026-06-14)

MY-DOGE-MICRO — local-first quantitative investment decision-support platform.
The **Release-Ready v1** baseline: brownfield clean-architecture migration
complete, all 10 ADRs Accepted, Verification → Release gate **clean PASS**.

### Three runtime surfaces (loopback-only)
- **PyQt desktop dashboard** — `src/interface/dashboard.py`
- **FastAPI HTTP backend** — `src/api/main.py` → `127.0.0.1:8901`
- **MCP server** — `doge_mcp.py` → stdio, or `127.0.0.1:8902` (SSE)

### Release certification
- Fresh `/architecture-review` **PASS** (0 CONCERNS) + fresh `/gate-check`
  Verification → Release **clean PASS** (2026-06-14).
- 10 ADRs Accepted (0001–0010). §6 layer-rule grep gate green (no direct
  `sqlite3`/`duckdb` in the interface layer).
- 579 pytest passed / 4 skipped / 0 failed; web build + 70 vitest green.

### Sprint 002 → 005 highlights
- **Sprint 002** (brownfield clean-architecture migration): ports & adapters
  (`IStockRepository`, `IReportRepository`, `INoteRepository`,
  `IMarketViewRepository`, `IMarketDataSource`, …), centralized settings
  (ADR-0002), error envelope (S002-009), SSE watchdog (S002-010),
  key→env (S002-013).
- **Sprint 003** (Verification): 3 product validation sessions, QA/smoke plan,
  performance baseline, RSRS sign fix (S003-005), API router DI.
- **Sprint 004** (Release clean PASS): TDX adapter implemented (ADR-0004
  Accepted), strengthened-loopback-guarantee (ADR-0007 Accepted),
  `INoteRepository` port + `notes.py`/`query_stock.py` off direct sqlite3
  (§6 gate green).
- **Sprint 005** (post-Release polish, Waves 1–4): retry consolidation
  (`_retry.py` + `YFinanceConfig`), yfinance adapter wiring (macro engine routes
  through the `IMarketDataSource` port), `scan.py` DI (`list_distinct_tickers`),
  SSE `str(e)` leak fixed, CLI bilingual remediation, traceability/manifest
  reconciliation.

### Load-bearing conditions (ADR-0007 loopback guarantee)
The CORS posture (`allow_origins=["*"]`) is safe ONLY because the API binds to
loopback. Two conditions MUST hold for the Release-Ready v1 posture:
1. The FastAPI process stays bound to `127.0.0.1:8901` — `_resolve_bind_host()`
   enforces this fail-closed (`DOGE_BIND_HOST` outside the loopback set raises).
2. No remote-client / non-loopback deployment model is supported.

Re-evaluate (CORS allow-list hardening + auth — ADR-0007 path 1a) before any
non-loopback deployment.

### Deferred (post-Release, non-blocking)
- Full yfinance-metadata adapter (ADR-0009 follow-on implementation).
- Bundled sample-data first-run demo (operator convenience; the deterministic
  mocked-yfinance contract test is delivered).
- Wave-5 hygiene: test-bootstrap `sys.path` consolidation, MCP tool error-text
  sanitization, `wmic` → CIM migration (Win11/Server 2025 portability).
- Auth + non-loopback CORS hardening (ADR-0007 path 1a) — only if the deployment
  model changes.

---

## Earlier — CDD template history (pre-product)

### Customer Delivery Hardening
- Enforced full strict lint across all 78 skills.
- Repaired customer-visible Markdown errors in required workflow skills.
- Aligned `UPGRADING.md` with the current workflow catalog and evidence paths.
- Made `/team-release` a required Release phase step after `/release-checklist`
  and `/launch-checklist`.
- Synchronized the documented template count with the actual template tree.
- Added support, security, contribution, changelog, and release-note documents.
- Strengthened workflow consistency checks for phase boundaries, release order,
  evidence paths, art bible phase status, and template counts.

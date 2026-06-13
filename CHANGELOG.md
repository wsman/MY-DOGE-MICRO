# Changelog

All notable changes to **MY-DOGE-MICRO** are recorded here.

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
- Enforced full strict lint across all 74 skills.
- Repaired customer-visible Markdown errors in required workflow skills.
- Aligned `UPGRADING.md` with the current workflow catalog and evidence paths.
- Made `/team-release` a required Release phase step after `/release-checklist`
  and `/launch-checklist`.
- Synchronized the documented template count with the actual template tree.
- Added support, security, contribution, changelog, and release-note documents.
- Strengthened workflow consistency checks for phase boundaries, release order,
  evidence paths, art bible phase status, and template counts.

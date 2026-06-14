# Release Checklist: v0.2.1 — Product (all)

Generated: 2026-06-14

## Release Candidate Metadata

| Field | Value |
|---|---|
| Version | **v0.2.1** |
| Branch | `cdd-adoption-2026-06-11` |
| Release commit | `705e2f3` + `7217821` release-metadata commit (this checklist, `CHANGELOG.md`, `pyproject.toml`) |
| Previous release | `v0.2.0` (`ad45634`) |
| Product type | Local-first quantitative investment decision-support platform |
| Deployment model | Single-operator, loopback-only (`127.0.0.1:8901` / `:8902`) |

## Scope Summary

`v0.2.1` is a patch release that folds the post-`v0.2.0` architecture-hygiene
tail into the Release baseline and aligns package metadata with the git tag.
The only code change since `v0.2.0` is the S006-006 migration of
`src/ai_analysis/fetch_names.py` onto the `ITickerMetadataSource` port.

---

## Codebase Health

- TODO count: **0**
- FIXME count: **0**
- HACK count: **0**
- `pyproject.toml` version: **0.2.1** ✅ (aligned with git tag)
- `CHANGELOG.md` `v0.2.1` section: ✅ present
- Secrets/credentials in code: **none found** (forensic audit confirmed no real
  `DEEPSEEK_API_KEY` ever committed)

---

## Build & Deploy Verification

- [x] Clean Python install / editable build succeeds (`pip install -e .`)
- [ ] No linter/type warnings — **not configured** (project has no lint/type gate)
- [x] All static assets / bundled data included (`data/*.db` referenced by demo)
- [x] Build version number correctly set (`pyproject.toml` → `0.2.1`)
- [x] Build reproducible from tagged commit
- [ ] Deploy pipeline tested — **N/A** (local desktop / CLI / MCP product)
- [ ] Database migrations tested forward/reverse — **N/A** (schema auto-created)

---

## Quality Gates

- [x] Zero S1 (Critical) bugs
- [x] Zero S2 (Major) bugs
- [x] All critical path workflows tested and signed off
- [x] Performance within budgets:
  - [x] MCP tool latency ≤ 30s
  - [x] Memory bounded by local dataset size
  - [x] UI long-running tasks off main thread (SSE scan/macro)
  - [x] No data-integrity defects identified
- [x] No regression from `v0.2.0`
- [ ] Extended soak/load test — **not executed** (local-first bounded dataset)

**Verification evidence** (current run / HEAD):
- `python -m pytest -q` → **617 passed, 5 skipped, 0 failed**
- `cd web && npm test` → **70 passed**
- `cd web && npm run build` → **green**
- `python src/cli.py demo --market cn --top 3` → exits 0 without `DEEPSEEK_API_KEY`
- §6 layer gate → **ZERO hits**

---

## Security

- [x] Secrets audit clean (no credentials in code, logs, or build artifacts)
- [x] API auth/authorization posture documented — **local-first, no auth by design**
- [x] Rate limiting — **N/A** (loopback-only)
- [x] CORS configuration correct for declared deployment model
  - `allow_origins=["*"]` is intentionally permissive.
  - Safe **only because** FastAPI binds to loopback (`127.0.0.1:8901`) via a
    fail-closed `_resolve_bind_host()` assertion.
- [x] TLS/HTTPS — **N/A** (loopback-only)
- [x] Privacy policy — **N/A** (local tool, no telemetry)

**Load-bearing conditions** (must hold for this release to remain secure):
1. The FastAPI process must stay bound to `127.0.0.1:8901` (default; non-loopback
   `DOGE_BIND_HOST` is rejected).
2. No remote-client / non-loopback deployment model is supported.

> **ADR-0007 path 1a** (explicit CORS allow-list + auth before non-loopback bind)
> remains conditionally deferred. If the deployment model ever changes, path 1a
> must be implemented **before** changing the bind host.

---

## Architecture Decision Records

| ADR | Status | Release Relevance |
|---|---|---|
| ADR-0001 | Accepted | Brownfield clean-architecture migration; §6 layer gates green |
| ADR-0002 | Accepted | Centralized configuration |
| ADR-0003 | Accepted | Retention policy (730 days) |
| ADR-0004 | **Accepted** (S004-004) | `TDXDataSource` implemented; no `NotImplementedError`; `tdx_downloader.py` is a thin CLI shim |
| ADR-0005 | Accepted | Error envelope |
| ADR-0007 | **Accepted** (S004-008b) | Loopback-guaranteed CORS posture; non-loopback hardening deferred to path 1a |
| ADR-0008 | Accepted | Event-driven / SSE watchdog |
| ADR-0009 | Accepted | `ITickerMetadataSource` + `YFinanceMetadataSource` |
| ADR-0010 | Accepted | `IMarketViewRepository` + view service injection |

> Stale concern corrected: ADR-0004 and ADR-0007 are both **Accepted**; neither
> is a current blocker or concern. The `polish-pass-2026-06-14.md` assessment
> pre-dates Sprint 004/005/006 and has been superseded by subsequent acceptance.

---

## Layer-Gate Verification

Re-verified with `rg` on current code:

- `src/api/routers/scan.py`: no literal `sqlite3.connect`, `connect_duckdb`, or
  `sys.path.insert`. Uses `IStockRepository` (injected), `SQLiteStorageRepository`,
  centralized `get_settings()`, and `ViewService.refresh_views`. Legacy TDX
  downloader is invoked as a functional shim, not as a layer bypass.
- `src/api/routers/notes.py`: no `sqlite3`, `connect_duckdb`, `sys.path.insert`,
  or legacy `stock_notes` import. All handlers depend on `INoteRepository` via
  `deps.get_note_repository`.
- `src/doge/`: `sys.path.insert` gate green.

> Stale concern corrected: the cross-layer bypasses flagged in the Sprint 003
> polish pass have been remediated in Sprint 004/005/006.

---

## Product-Specific: API

- [ ] OpenAPI/Swagger spec manually reviewed against implementation — **not done**
- [x] Endpoints respond within budget
- [x] Error responses follow project convention (`{"error":{"code","message"}}`)
- [x] Rate limiting/pagination tested where applicable
- [ ] API versioning strategy documented — **not formalized**
- [ ] Deprecated endpoints with sunset dates — **N/A**

---

## Product-Specific: Web

- [x] Responsive layout tested
- [x] Browser compatibility verified (Chrome 126)
- [ ] Formal accessibility audit — **not executed**
- [ ] Core Web Vitals measured — **not executed**
- [ ] Progressive enhancement without JS — **not verified**
- [ ] Sitemap / robots.txt — **N/A**

---

## Product-Specific: CLI

- [x] Help text accurate for all commands/subcommands
- [x] Exit codes consistent (`EXIT_NO_DATA=1` on no-data paths)
- [ ] Shell completion scripts — **not provided**
- [ ] Man page / generated reference docs — **not provided**
- [x] Installation documented and tested (`pip install -e .`)

---

## Launch Readiness

- [ ] Analytics / telemetry verified — **not configured**
- [ ] Crash reporting configured — **not configured**
- [ ] Day-one patch — **N/A**
- [ ] On-call schedule — **N/A (single-operator)**
- [ ] Community announcements drafted — **N/A**
- [ ] Support team briefed — **N/A**
- [ ] Rollback plan documented — **not provided**

---

## Go / No-Go

**Verdict: READY**

**Rationale:**
- The only code change since `v0.2.0` is S006-006 (`fetch_names.py` metadata-port
  migration), which is fully tested and verified.
- Package version (`pyproject.toml`) is now aligned with the release tag.
- All active ADRs are Accepted; no architecture concern remains open.
- Full verification suite is green (617 pytest / 5 skip / 0 fail; 70 vitest;
  web build green; demo exits 0 without an API key).
- The deferred ADR-0007 path 1a is explicitly scoped to a future non-loopback
  deployment model and does not affect this patch release.

**Remaining advisory gaps (do not block v0.2.1):**
1. No formal CI/CD pipeline (local verification only).
2. No formal a11y / Core Web Vitals audit.
3. No shell completion / man page.
4. No telemetry / crash reporting.
5. ADR-0007 path 1a remains conditionally deferred.

---

## Sign-offs Required

- [ ] QA Lead
- [ ] Technical Director
- [ ] Producer / Product Owner
- [ ] Operator (single-operator project — WSMAN)

---

## Next Steps

1. Operator sign-off on this checklist.
2. Run `/launch-checklist` for final launch orchestration.
3. Create and push annotated tag `v0.2.1` on the release-metadata commit.
4. Optionally run `/team-release` for release-day coordination.

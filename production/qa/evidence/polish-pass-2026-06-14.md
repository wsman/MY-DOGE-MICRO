# Polish Pass — MY-DOGE-MICRO Release-Readiness (Verification → Release)

> **Date:** 2026-06-14
> **Scope:** Product-branch `/team-polish` pass — Phase 3 (Reliability & Release Hardening) synthesis of Phase 1/2/4 dimension assessments
> **Methodology:** team-polish PRODUCT-BRANCH (SKILL.md). Assessment-only pass — no code, ADR, test, or other file modified. ADR promotion decision is deferred to the operator (Phase 4 A/B).
> **Stage:** Verification (Sprint 003 closure). Local-first, single-operator, loopback-only (`127.0.0.1:8901`), no-auth-by-design.
> **Governing review:** `production/architecture-reviews/architecture-review-s003-014-2026-06-13.md` — verdict **CONCERNS**, 5 closure conditions.
> **Validation basis:** 3 product validation reports (`user-test-001/002/003-2026-06-13.md`) + 72 governance/layer-gate/contract/adapter tests green + 508 pytest/0xfail + 70 vitest per session memory.

---

## Overall Verdict: **READY FOR RELEASE** (governed-advisory, CONCERNS recorded)

The product is releasable as a **governed-advisory Release under a recorded risk note**. The blockers list is **empty** — no functional regression, no data-integrity defect, and no breached security boundary was identified across the five assessed dimensions. The outstanding items are *advisory concerns* that are either (a) documented Wave-5 deferrals already ratified by the S003-014 architecture review, (b) operator-facing documentation drift, or (c) intentional ADR-Proposed positions whose promotion gates are explicitly tracked post-Verification.

This verdict is the team-polish Phase 3/4 synthesis, grounded in the dimension assessments. The operator must make the final Phase 4 A/B decision (see Phase 4 Recommendation below); per the Error Recovery Protocol and Phase 2 contract-preservation rule, **no Proposed-ADR-scope fix was implemented in this pass** — both ADRs are ASSESSED only.

---

## Dimension Findings (with file:line evidence)

### D1 — Reliability / Network-call degradation (yfinance rate-limit)
**Rating: concern (not blocker, not release-ready-clear)**

The yfinance adapter itself is correct and fully tested. The user-test-002 PARTIAL verdict is an **environmental artifact** (Yahoo upstream "Too Many Requests"), not a code defect: the adapter degraded from safely to `None` exactly as designed.

- **Adapter retry/degradation path is correct (no code defect)** — `src/doge/infrastructure/data_source/yfinance.py:64-72` (`_is_rate_limited()`), `:216-254` (`_fetch_with_retry()`, bounded `max_retries=3`, fixed `retry_delay=5.0s`, retries empty responses, logs warnings on rate-limit, returns `None` after exhaustion). Contract docstring at `:159-165` guarantees "Never raises for transient/empty conditions." `tests/test_yfinance_adapter.py`: 13/13 network-free tests cover retry-then-succeed and exhausted-retries. `production/qa/evidence/user-tests/user-test-002-first-run-result.json:57-61`: upstreamSignal `YFRateLimitError: Too Many Requests`, verdict `safe_degradation`.
- **Graceful degradation NOT in operator docs (concern)** — `design/cdd/data-sources.md:171,282` specifies the behavior; but `docs/operations-runbook.md:169,374` and `docs/GETTING_STARTED.md` do not surface yfinance 429 symptoms / retry budget.
- **Adapter not wired into any product runtime path (concern)** — `YFinanceDataSource` is referenced only in its own package, tests, CDD, ADR-0004, and ADR-lifecycle test governance — no service/router/CLI/scanner import. The macro engine still calls `yfinance.download` directly (`src/macro/data_loader.py:82`, its own duplicate retry loop `:76-108`). The first-run "ingest" was a one-off adapter exercise, not a real product workflow.
- **Retry knobs are module-level constants (nit)** — `DEFAULT_MAX_RETRIES=3` (`yfinance.py:60`), `DEFAULT_RETRY_DELAY=5.0` (`:61`), `DEFAULT_PERIOD_DAYS=120` (`:59`). `design/cdd/data-sources.md §8` Acceptance Criteria lists `YFinanceConfig` migration as OPEN. Standards/coding-standards.md forbids hardcoded timeouts; tracked as ADR-0004 promotion follow-up.

### D2 — ADR-0004 / ADR-0007 governance release-readiness (ASSESS ONLY)
**Rating: concern (both ADRs intentionally Proposed; deferrals sound; not hard blockers)**

- **ADR-0004 (TDX adapter stub) deferral is sound** — `src/doge/infrastructure/data_source/tdx.py:32,35` both raise `NotImplementedError`. The operator's live CN-data path `src/micro/tdx_downloader.py` still exists on disk — **no functionality is lost**. The yfinance half of the contract is fully shipped and green (13/13 tests).
- **ADR-0007 (CORS hardening) deferral is sound while loopback bind holds** — `src/api/main.py:37` `allow_origins=['*']` is permissive; `src/api/main.py:115` `uvicorn.run(app, host='127.0.0.1', port=8901)` is loopback-only. The ADR's "Deferral Decision (S003-013)" block makes the security argument explicit and forbids non-loopback exposure. The error-envelope half is DONE (two global handlers at `src/api/main.py:54,69`; contract regression at `tests/contract/test_api_error_envelope.py`).
- **Operative release contract = S003-014 CONCERNS verdict + 5 conditions, NOT the ADR Status field** — `production/architecture-reviews/architecture-review-s003-014-2026-06-13.md` lists 5 conditions that must remain true; condition (2)/(5) actively enforced by `tests/unit/governance/test_adr_lifecycle_status.py:58-75` (hard-asserts Proposed + REMAINS keywords). 72 governance/layer-gate/contract/adapter tests green.
- **Stale traceability text on src/api DB usage (nit)** — S003-014 Non-Blocking Notes flag traceability text describing direct SQLite/DuckDB in `src/api` as outstanding; this is stale relative to S003-003. Documentation/traceability drift only — not a code or ADR-status issue.

### D3 — API Layer Gate — direct DB usage in src/api
**Rating: concern (literal §6 grep passes for src/api; §6 fails for interfaces scope; cross-layer bypasses in scan.py / notes.py)**

- **scan.py imports infrastructure-layer adapter and runs raw SQL across the layer boundary (concern)** — `src/api/routers/scan.py:28` `from doge.infrastructure.database.sqlite import SQLiteConnection`; `:205-207` `SQLiteConnection(db_path).execute("SELECT DISTINCT ticker FROM stock_prices")`; `:27,29` imports `composition.refresh_views` and `sqlite_storage.SQLiteStorageRepository`. Adapter at `src/doge/infrastructure/database/sqlite.py:6,30` does `sqlite3.connect` internally. Bypasses the `deps.py` DI seam.
- **notes.py delegates every handler to a legacy module doing sqlite3.connect + connect_duckdb directly (concern)** — `src/api/routers/notes.py:26,36,50,57,63,75` all call into `src.ai_analysis.stock_notes`; callee `src/ai_analysis/stock_notes.py:14` imports `connect_duckdb`, `:25` `sqlite3.connect(NOTES_DB)`, raw SQL at `:38,41,57,86,112,128,131,137,154,159,188,205,223,241`. Transitive coupling not surfaced by the §6 grep.
- **Literal §6 grep gate FAILS for broader interfaces scope (concern)** — `control-manifest.md §6` (lines 188-191) specifies grep over `src/api src/doge/interfaces src/interface`. `src/doge/interfaces/mcp/tools/query_stock.py:4` `import sqlite3`; `:92` `sqlite3.connect(...)`. Gate is RED for the interfaces scope.
- **Governance contradiction (concern)** — `production/sprints/sprint-003-verification.md:146` marks `[x]` "no direct sqlite3.connect / connect_duckdb" while `production/milestones/verification-milestone.md:40` leaves it `[ ]` and `:53` leaves Layer-rule grep gate `[ ]`. The two docs must reconcile to a single truthful state.
- **Macro/scan legacy-module coupling (nit, Wave-5)** — `src/api/routers/macro.py:78-80` imports `GlobalMacroLoader`/`DeepSeekStrategist`/`save_macro_report` from `src.macro`/`src.micro`; `src/api/routers/scan.py:185-187,277` import legacy `src.micro`. Permitted under control-manifest §2 legacy-tolerance clause.

### D4 — CONTRACTS / ERGONOMICS (API / CLI / SSE)
**Rating: release-ready**

All three contract surfaces are SHIPPED, DOCUMENTED, TESTED, and GREEN.

- **API error envelope** — every `HTTPException` reshaped to `{"error":{"code","message"}}`; full string-enum code set + fallback `http_{status}`; catch-all `Exception` handler returns fixed operator-safe message with zero `str(e)` leak. `tests/contract/test_api_error_envelope.py` (8 cases) + `tests/contract/test_api_doc_route_coverage.py` (7 cases) green. user-test-003 confirms `POST /api/scan/bad → 400 {"error":{"code":"bad_request",...}}`.
- **CLI exit codes** — `src/cli.py:41` `EXIT_NO_DATA = 1`; `:89,102,120,133` call `sys.exit(EXIT_NO_DATA)` on no-data path; `tests/cli/test_cli_service_dispatch.py` (8 cases). `src/macro/cli.py` exits 1 on market-data-None and on any exception with API-key redaction (`tests/cli/test_macro_cli_error_redaction.py`). user-test-003 confirms macro.cli exit 1 on missing `DEEPSEEK_API_KEY`.
- **SSE contract** — S002-010 watchdog shipped client-side (`web/src/composables/useSSE.spec.ts` driving `idle|running|error|complete` state machine in `ScannerView.vue`). user-test-003 confirms `POST /api/scan/us → SSE progress=100 message=done`.

Advisory nits only (none block release): `docs/CLI.md:247-251` exit-code table is stale (describes 0-on-no-data vs shipped EXIT_NO_DATA=1); SSE in-band `progress=-1` carries raw `str(e)` at `src/api/routers/scan.py:251-253` and `src/api/routers/macro.py:105` (out of HTTP-envelope scope, loopback-only); 422 `RequestValidationError` intentionally NOT enveloped at `src/api/main.py:85-89` (tracked S002-011); macro CLI mixes English exception text with Chinese remediation hint (`src/macro/cli.py:109-111`); server-side `_scan_status` map exposes `idle|running` only (`src/api/routers/scan.py:47,160,257`), terminal `error|complete` live client-side only.

### D5 — Validation Coverage (team-polish Phase 4 + Verification→Release gate)
**Rating: concern (gate's 3-distinct-scenario requirement satisfied; one first-live-ingest gap remains)**

- **3 reports map cleanly to gate's 3 required scenarios** — user-test-001 (core workflow, PASS) / user-test-002 (first-run, PARTIAL) / user-test-003 (failure/recovery, PASS). Distinct, no overlap.
- **user-test-002 PARTIAL is gate-acceptable** — all first-run *scenario mechanics* passed (editable install, fresh `DOGE_DB_DIR` startup, empty-DB init, empty scanner path, empty archive query). Only gap: first live yfinance write blocked by upstream Yahoo rate-limit; adapter degraded safely with no DB corruption. Gate requires a first-run *scenario*, not a successful first live data write.
- **First-live-ingest coverage gap to close before Release (concern)** — add a bundled sample-data / fixture-backed first-run demo (per report's own Priority #3). Do NOT rely on a Yahoo re-run (non-deterministic, violates standards/coding-standards.md Automated Test Rules). A mocked yfinance contract test is the complementary automated close.
- **Template/consistency nits** — user-test-002 and user-test-003 fully signed against Product Validation Template (Build/Commit `1cba49b`); user-test-001 uses older story-evidence format (lacks Build/Commit and Surface fields). user-test-001 PASS cites adjusted "read-side" acceptance criteria — verify scope drift is intentional in S003-002 story.

---

## Consolidated Blockers (must-fix-before-Release)

**None.**

No functional regression, no data-integrity defect, no breached security boundary, no missing functional path (TDX works via `src/micro/tdx_downloader.py`; loopback bind holds for ADR-0007). The blockers list is empty.

## Consolidated Concerns (advisory / deferrable-with-recorded-risk-note)

1. **Governance contradiction in tracker docs** — `production/sprints/sprint-003-verification.md:146` marks API-DI `[x]` while `production/milestones/verification-milestone.md:40` leaves `[ ]`. Reconcile to a single truthful state (flip sprint-003:146 back to `[ ]` OR amend wording to "literal sqlite3.connect/connect_duckdb removed; cross-layer adapter + transitive legacy coupling deferred to Wave 5"). Correct the S003-014 review note to acknowledge scan.py `SQLiteConnection` cross-layer import and notes.py transitive coupling rather than dismissing as "stale text." *Highest-priority advisory — pure documentation reconciliation, zero code risk.*
2. **§6 grep gate is RED for interfaces scope** — `src/doge/interfaces/mcp/tools/query_stock.py:4,92` (`import sqlite3` + `sqlite3.connect`). Migrate to injected `IStockRepository`/`ISchemaBrowser` port. Until then, verification-milestone §6 line 53 checkbox must stay `[ ]`; any "§6 gate green" claim must be explicitly scoped to `src/api` only.
3. **Cross-layer bypasses in src/api/routers/{scan,notes}.py** — `scan.py:28,205-207` (raw SQL via `SQLiteConnection`) and `notes.py:26-75` (transitive coupling to `src/ai_analysis/stock_notes`). Port behind `IStockRepository`/`INoteRepository` via `deps.py`, or formally record as Wave-5 brownfield offenders per control-manifest §2 legacy-tolerance clause.
4. **Operator docs do not surface yfinance graceful degradation** — add a "First-run / yfinance rate limiting" subsection to `docs/operations-runbook.md` and a one-paragraph note in `docs/GETTING_STARTED.md`: symptoms (`yfinance returned None` / 0 rows on first ingest), root cause (Yahoo HTTP 429, environmental not a bug), retry budget (3 × 5s ≈ 15s).
5. **Adapter not wired into product runtime path** — note in runbook/GETTING_STARTED that live yfinance OHLCV ingest into `stock_prices` is not yet wired through the product; first-run data still requires the TDX downloader or manual yfinance pull.
6. **First-live-ingest coverage gap** — add bundled sample-data / fixture-backed first-run demo + mocked yfinance contract test (deterministic close per user-test-002 Priority #3).
7. **docs/CLI.md exit-code table stale** — `docs/CLI.md:247-251` describes 0-on-no-data vs shipped `EXIT_NO_DATA=1` (`src/cli.py:41`). Update the table; remove the ⚠️ tech-debt note.
8. **SSE in-band `progress=-1` carries raw `str(e)`** — `src/api/routers/scan.py:251-253`, `src/api/routers/macro.py:105`. Route through operator-safe fixed string or add redaction pass; document chosen behavior in `docs/API.md §SSE Contract`. Loopback-only, low release risk.
9. **Macro CLI mixes English exception text with Chinese remediation hint** — `src/macro/cli.py:109-111`. Consolidate into a single concise bilingual remediation block.
10. **Stale traceability text on src/api direct DB usage** — update during final Sprint 003 closure rollup or next architecture-traceability refresh.
11. **Retry knobs are module-level constants** — promote to `YFinanceConfig` dataclass in `settings.py` per ADR-0004 / CDD §8 open acceptance criterion.

---

## ADR-0004 / ADR-0007 Disposition (ASSESS ONLY — per team-polish Error Recovery Protocol, Proposed-ADR fixes are NOT implemented in a polish pass)

| ADR | Recommendation | Rationale (grounded in findings + S003-014 CONCERNS review) |
|---|---|---|
| **ADR-0004** (Data-source adapter contract — TDX stub) | **defer-with-recorded-risk-note** | yfinance half fully shipped and green (13/13 network-free tests, correct retry/degradation). TDX stub at `src/doge/infrastructure/data_source/tdx.py:32,35` raises `NotImplementedError`, but live CN-data path `src/micro/tdx_downloader.py` remains — **no functionality is lost**. The deferral is a quality/tech-debt concern, not a functional regression or safety breach. S003-014 review ruled "Yes, with CONCERNS" that ADR-0004 may stay Proposed through Sprint 003 closure; promotion now "would overstate the architecture state." Promotion gate (4 items) is explicitly tracked post-Verification. |
| **ADR-0007** (API surface + CORS hardening) | **defer-with-recorded-risk-note** | Error-envelope half DONE (S002-009: two global handlers at `src/api/main.py:54,69` + contract regression test). CORS-hardening half REMAINS: `allow_origins=['*']` at `src/api/main.py:37` is permissive but the bind is loopback-only (`host='127.0.0.1'` at `:115`) and the platform is single-operator local-first with no auth by design. The ADR's Deferral Decision (S003-013) block makes the security argument explicit and forbids non-loopback exposure before CORS + auth. S003-014 ruled "Yes, with CONCERNS." Acceptable under CONCERNS **only while the loopback bind holds** — release notes must prominently state the two load-bearing conditions. |

**Common rationale:** Both ADRs are intentionally Proposed with documented, sound deferral rationales and are actively pinned by `tests/unit/governance/test_adr_lifecycle_status.py:58-75`. The operative release contract is the S003-014 CONCERNS verdict + its 5 closure conditions, not the ADR Status field. Neither qualifies as a `hard-blocker` because no functionality is missing and no security boundary is breached. `promote-to-Accepted` is **not** appropriate in this assessment pass — it would require new implementation work (Phase 4 path A), which the team-polish orchestrator does not perform.

---

## Phase 4 Recommendation

**Recommendation: (B) Accept CONCERNS Release with a recorded risk note under governed-advisory.**

**Basis:** The blockers list is **empty**. Per the team-polish decision rule, when no blockers exist, path (B) is viable. The CONCERNS posture is precisely the S003-014 review's ruling and is consistent with the local-first, loopback-only, single-operator deployment model. The 11 advisory concerns are all either documentation drift, ratified Wave-5 deferrals, or intentionally-tracked ADR-Proposed positions — none of which impair Release under a governed-advisory posture.

**Required Release-Notes risk note (verbatim recommendation):**

> Two ADRs (0004 TDX adapter, 0007 CORS hardening) remain Proposed by design; both are tracked as post-Verification work; neither affects local-first single-operator operation. Two load-bearing conditions must hold for ADR-0007's deferral to remain valid: (1) the FastAPI process must remain bound to `127.0.0.1:8901`, and (2) no remote-client / non-loopback deployment model is supported. Re-evaluate before any non-loopback deployment or before retiring the legacy TDX path at `src/micro/tdx_downloader.py`. The S003-014 architecture review's 5 closure conditions remain the operative release contract and are enforced by `tests/unit/governance/test_adr_lifecycle_status.py`.

**If the operator prefers path (A) clean PASS (promote ADRs first via new implementation sprint):** the concrete work is —
- **ADR-0004:** (1) implement `TDXDataSource` without `NotImplementedError`, (2) migrate/thin-wrap `tdx_downloader.py` through the port, (3) add deterministic tests or documented live-smoke evidence, (4) re-run governance tests then flip Status to Accepted.
- **ADR-0007:** (1a) implement explicit CORS allow-list (`APIConfig.cors_origins` on Settings, defaulting to Vue dev + Tauri origins) **OR** (1b) write a strengthened-loopback-guarantee decision accepted by a fresh `/architecture-review`, plus (2) add auth before any non-loopback bind, then (3) re-run API contract/governance tests.

---

## Sign-off

- **Pass type:** Assessment only (team-polish Product Phase 3 synthesis). No code, ADR, test, or other file modified.
- **Operator action required:** Phase 4 A/B decision (recommendation: B). ADR promotion decision is deferred to the operator per the team-polish Error Recovery Protocol.
- **Next-step skills:** If operator chooses (B) → `/release-checklist`. If operator chooses (A) → `/sprint-plan` update for the ADR-promotion sprint, then re-run `/team-polish` after fixes. For a formal phase gate verdict before release hand-off → `/gate-check`.
- **Artifact path:** `production/qa/evidence/polish-pass-2026-06-14.md`

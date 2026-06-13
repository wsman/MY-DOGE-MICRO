# Architecture Review Brief: Sprint 003 Verification

> **Review ID**: S003-014
> **Stage**: Verification
> **Date**: 2026-06-13
> **Review Type**: Fresh `/architecture-review` (Step 2) — ADR state promotion gate
> **Scope**: ADR-0004 and ADR-0007 promotion eligibility; Sprint 003 closure readiness

---

## 1. Context

This brief initiates Step 2 of the Verification stage architecture review cycle. Sprint 003 has delivered 10 of 13 stories (S003-001, S003-003, S003-005, S003-006 through S003-009, S003-011, S003-012, S003-013). The remaining 3 stories are architectural and governance items that gate Sprint 003 closure and the Verification → Release transition.

The reviewer's task is to render a verdict on whether Sprint 003 may close with ADR-0004 and ADR-0007 remaining in **Proposed** state, or whether either ADR must be promoted to **Accepted** (or downgraded) before the sprint can be marked complete.

---

## 2. Prerequisites Met (Verified)

| Story | Deliverable | Status | Evidence |
|---|---|---|---|
| S003-003 | API router dependency injection | Done | `src/api/routers/` refactored; no direct `sqlite3.connect` / `connect_duckdb` in routers; contract tests green |
| S003-005 | RSRS DuckDB view sign convention fix | Done | `vw_rsrs_ranking` sign convention aligned with Python RSRS path; xfail removed |
| S003-013 | CORS deferral formally recorded | Done | ADR-0007 §Deferral Decision (S003-013, 2026-06-12) written; deferral rationale documented |

These three prerequisites satisfy the gate-check Technical Director concerns that were explicitly deferrable into Verification. They are not themselves in question during this review.

---

## 3. Ruling Questions for the Reviewer

### 3.1 ADR-0004: Data Source Adapter Contract

**Current state**: `Proposed` (since 2026-06-11; last verified 2026-06-12).

**What is done**: `IMarketDataSource` port exists; `YFinanceDataSource` adapter implemented and green (13/13 tests, network-free); `tdx_downloader.py` remains functional as a legacy compatibility shim.

**What remains**: `TDXDataSource` (`src/doge/infrastructure/data_source/tdx.py`) still raises `NotImplementedError` at `:32` (`download_kline`) and `:35` (`get_latest_market_date`). The migration of `src/micro/tdx_downloader.py` onto the port is deferred to post-Verification (see `production/milestones/verification-milestone.md` §Deferred to Post-Verification).

**Question for reviewer**: May Sprint 003 close with ADR-0004 remaining **Proposed**, given that:
- The TDX adapter stub is explicitly deferred to a post-Verification sprint (low user impact; `tdx_downloader.py` remains functional);
- The YFinance adapter is complete, tested, and in production use;
- The ADR's Validation Criteria checklist records the TDX item as pending, not hidden.

Or does the reviewer require ADR-0004 promotion to **Accepted** now, which would block Sprint 003 closure until the TDX adapter is implemented?

### 3.2 ADR-0007: API Surface and CORS

**Current state**: `Proposed` (since 2026-06-12; deferral decision S003-013 added same day).

**What is done**: Error envelope fully implemented — two global exception handlers (`@app.exception_handler(HTTPException)` + `@app.exception_handler(Exception)`) registered in `src/api/main.py`; six `try/except ... raise HTTPException(500, str(e))` wrappers removed from `data.py` and `notes.py`; regression locked behind `tests/contract/test_api_error_envelope.py`.

**What remains**: CORS hardening — `allow_origins=["*"]` (`src/api/main.py:28`) remains permissive. The server binds to `127.0.0.1:8901` (loopback-only). No authentication is in scope (local-first design constraint).

**Question for reviewer**: Is the combination of **loopback-only bind** (`127.0.0.1:8901`) + **`allow_origins=['*']`** an acceptable security posture for the Verification stage, such that ADR-0007 may remain **Proposed** through Sprint 003 closure?

The security argument (recorded in ADR-0007 §Deferral Decision) is:
- The platform is single-operator, local-first, with no remote clients in scope;
- The bind is loopback-only; no remote client can reach the API in the default deployment;
- The permissiveness is safe **only because** of the loopback bind; it is not safe under any other bind;
- A non-loopback `bind_host` (e.g., `0.0.0.0`) is **explicitly gated** on CORS tightening + auth addition, in that order.

Does the reviewer accept this argument for the Verification stage, or does the reviewer require ADR-0007 promotion to **Accepted** now (which would require CORS hardening to land before Sprint 003 closes)?

---

## 4. Required Reviewer Output

The reviewer must produce a verdict with **exactly one** of the following labels:

- **PASS** — Sprint 003 may close with both ADR-0004 and ADR-0007 remaining **Proposed**. The deferred items are acceptable risk for the Verification stage. No additional action required before sprint closure.

- **CONCERNS** — Sprint 003 may close with both ADR-0004 and ADR-0007 remaining **Proposed**, but the reviewer documents specific conditions or follow-up items that must be tracked (e.g., "acceptable only if a post-Verification TDX story is scheduled within 2 sprints"; "acceptable only if loopback bind is verified by a smoke test").

- **FAIL** — Sprint 003 may **not** close until one or both ADRs are promoted to **Accepted**. The reviewer must state which ADR(s) block closure and what deliverable(s) would satisfy the promotion gate.

In all cases, the reviewer output must explicitly state:
1. Whether ADR-0004 may stay **Proposed** through Sprint 003 closure (yes/no + rationale).
2. Whether ADR-0007 may stay **Proposed** through Sprint 003 closure (yes/no + rationale).
3. Whether the overall Sprint 003 closure is **approved** (PASS/CONCERNS) or **blocked** (FAIL).

---

## 5. CONCERNS Summary (from Gate Report)

The following concerns from the Implementation → Verification gate check (`production/gate-checks/gate-implementation-verification-2026-06-12.md`) are relevant to this review:

**Technical Director concerns (directly applicable)**:
- ADR-0004 remains Proposed (TDX adapter stub) — the TDX adapter is not yet implemented; `tdx_downloader.py` remains a functional legacy shim.
- ADR-0007 remains Proposed (CORS hardening incomplete) — the CORS deferral is now formally recorded (S003-013), but the ADR itself stays Proposed through Verification.
- Direct DB connections remain in `src/api/routers/` and `src/api/main.py` — partially addressed by S003-003 (router DI done); any remaining direct connections should be flagged by the reviewer.
- DuckDB `vw_rsrs_ranking` sign convention was xfail-pinned — addressed by S003-005; no longer relevant.

**Other director concerns (context only, not ADR-gating)**:
- Creative Director: no user-validation evidence; missing per-view flow specs; accessibility OPEN items.
- Producer: no milestone deadline set (now set: 2026-06-26); Wave 5 deferred items could compress timeline.
- Art Director: no art bible / design tokens (now addressed by S003-007); per-view flow specs incomplete (now addressed by S003-006); loading/empty/error triad gaps (now addressed by S003-009).

This review focuses **only** on the ADR-0004 and ADR-0007 promotion questions. The non-ADR concerns are tracked in the Sprint 003 backlog and the Verification milestone exit criteria.

---

## 6. Constraints on the Reviewer

- **Do NOT modify ADR status fields** in `docs/architecture/adr-0004-*.md` or `adr-0007-*.md`. The status fields (`Proposed` / `Accepted` / `Superseded`) are owned by the review conclusion process, not by this brief. The reviewer's verdict drives the status change; the brief only frames the question.
- The reviewer may reference any file in the repository but must not write to ADR files as part of rendering the verdict.
- If the reviewer issues **FAIL**, the reviewer must specify the exact deliverable(s) that would convert the verdict to **PASS** or **CONCERNS**.

---

## 7. Related Artifacts

- Gate check report: `production/gate-checks/gate-implementation-verification-2026-06-12.md`
- ADR-0004: `docs/architecture/adr-0004-data-source-adapter-contract.md`
- ADR-0007: `docs/architecture/adr-0007-api-surface-and-cors.md`
- Verification milestone: `production/milestones/verification-milestone.md`
- Sprint 003 plan: `production/sprints/sprint-003-verification.md`
- Stage file: `production/stage.txt` (reads `Verification`)

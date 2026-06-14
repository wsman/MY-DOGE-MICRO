# Sprint 004 — Release clean-PASS prep

> **Stage**: Verification · **Predecessor**: Sprint 003 (Verification, 13/13 done)
> **Milestone**: `production/milestones/verification-milestone.md` (Verification / Release-Ready v1)
> **Duration**: 2026-06-13 → 2026-06-26 · **Control Manifest**: 2026-06-12 (rules unchanged; Sprint 004 enforces, does not alter)
> **Status**: **done** (8/8 stories; Verification → Release gate-check clean PASS; stage advanced to Release)

## Goal

Execute Phase-4 path (A) — pursue a **clean PASS** at the Verification → Release
gate by promoting both Proposed ADRs (0004, 0007) to Accepted and clearing the
layer-gate REDs the `/team-polish` pass (2026-06-14, READY-governed-advisory) +
the S003-014 architecture review flagged. The operator chose (A) clean PASS over
(B) accept-CONCERNS-Release.

## Milestone context

Sprint 003 closed 13/13 under a CONCERNS verdict (two Proposed ADRs + §6 layer
gate RED). The `/team-polish` pass confirmed READY FOR RELEASE (governed-
advisory, blockers empty, 11 advisory concerns) and recommended path (B); the
operator chose (A) — promote the ADRs + clear the gates for a clean gate-check.

## Scope

**In**: ADR-0004 promotion (TDX adapter), ADR-0007 promotion (strengthened-
loopback-guarantee, path 1b), §6 layer-gate cleanup (`INoteRepository` port +
`notes.py`/`query_stock.py` off direct sqlite3), milestone/DoD reconciliation,
operator doc fixes.

**Out (deferred)**: `_retry.py` shared-helper extraction (re-scoped to a
follow-on ADR; not an ADR-0004 promotion gate); full `scan.py` `Depends(repo)`
conversion (grep-clean today; §4.3-allowed adapter use); auth (only relevant if
a non-loopback deployment is ever introduced).

**Decisions (operator)**: ADR-0007 via path **(1b) strengthened-loopback-
guarantee** (not 1a explicit allow-list); notes port via **(split) new
`INoteRepository`** (not fold into `IReportRepository`).

## Story backlog

| Story | Title | Epic | TR | Pri | Effort | Owner | Status |
|-------|-------|------|----|-----|--------|-------|--------|
| S004-001/002 | INoteRepository port + adapter; notes.py off ai_analysis | ep-architecture-debt | TR-045 | HIGH | M | python-specialist | done |
| S004-003 | query_stock → get_ticker_with_context (§6 gate green) | ep-architecture-debt | TR-046 | HIGH | S | python-specialist | done |
| S004-004 | TDXDataSource real impl (ADR-0004 gate met) | ep-architecture-debt | TR-011 | HIGH | L | python-specialist | done |
| S004-005 | ADR-0007 strengthened-loopback-guarantee (path 1b) | ep-governance-security | TR-029/032 | MED | S | python-specialist | done |
| S004-006 | verification-milestone exit criteria all [x] | ep-governance-security | — | MED | S | lead-programmer | done |
| S004-007 | operator docs: yfinance rate-limit + CLI exit-code table | ep-governance-security | — | LOW | S | python-specialist | done |
| S004-008a | ADR-0004 → Accepted + TR-045/046 + TR-011 | ep-governance-security | TR-011 | MED | S | lead-programmer | done |
| S004-008b | ADR-0007 → Accepted + governance test | ep-governance-security | TR-029/032 | HIGH | S | lead-programmer | done |

## Open / blocked

- **S004-008b DONE** — fresh `/architecture-review` passed (PASS verdict) and ADR-0007 Status flipped to Accepted in commit `20ce713`.
- **Flagged for the arch-review**: `TDXDataSource.connect(self, market="cn")`
  widens the port signature `connect(self)` (Liskov-compatible; flagged in
  commit `b989ef9`). The review ruled this an acceptable adapter extension
  (documented in `architecture-review-s004-2026-06-14.md`).

## Definition of Done

- [x] §6 layer-rule grep gate green (`src/api` + `src/doge/interfaces` + `src/interface` → 0 hits).
- [x] `python -m pytest -q` green (566 passed, 4 skipped, 0 failed).
- [x] ADR-0004 Accepted.
- [x] ADR-0007 Accepted (S004-008b, post-arch-review).
- [x] Fresh `/architecture-review` → PASS verdict + ADR-0007 authorization.
- [x] Fresh `/gate-check` (Verification → Release) → **clean PASS**; stage advanced to Release.

## Related artifacts

- Plan: `C:\Users\WSMAN\.claude\plans\14-stateless-kahn.md` (Sprint 004 section).
- Polish pass: `production/qa/evidence/polish-pass-2026-06-14.md`.
- Prior review: `production/architecture-reviews/architecture-review-s003-014-2026-06-13.md`.
- Arch-review brief: `production/architecture-reviews/architecture-review-brief-s004.md`.
- Arch-review report: `production/architecture-reviews/architecture-review-s004-2026-06-14.md`.
- Commits: `b44d6a7`→`20ce713` (11 commits).

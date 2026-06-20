# Architecture Review Brief — Sprint 004 (Release clean-PASS prep)

> **Date**: 2026-06-14 · **Prior review**: `architecture-review-s003-014-2026-06-13.md` (CONCERNS)
> **Scope**: focused review of the Sprint 004 ADR promotions + layer-gate cleanup,
>   as the independent authority for the Verification → Release clean-PASS gate.
> **Run in a FRESH Claude Code session** (this session implemented the work — it
>   cannot self-certify).

## Why this review

Sprint 004 executed Phase-4 path (A): pursue a clean PASS at the Verification →
Release gate by promoting both Proposed ADRs + clearing the layer-gate REDs the
polish pass + S003-014 flagged. The code work is committed (7 commits,
`b44d6a7`→`c78498b`); 568 pytest passed / 2 skipped / 0 failed; §6 layer gate
green. This review is the **independent sign-off** before the fresh `/gate-check`.

## Ruling questions (in priority order)

### 1. ADR-0007 — authorize the strengthened-loopback-guarantee promotion (PRIMARY)
ADR-0007 (API surface + CORS) stays Proposed; its promotion path (1b) is gated on
a fresh `/architecture-review` sign-off (ADR-0007:46-49 — this review is that
authority). S004-005 implemented the guarantee:
- `src/doge/interfaces/api/main.py`: `_resolve_bind_host()` asserts the bind host is loopback
  (`127.0.0.1`/`localhost`/`::1`); `__main__` calls it via `DOGE_BIND_HOST`.
  Any non-loopback bind raises `AssertionError` (fail-closed) before
  `uvicorn.run`. CORS stays `allow_origins=["*"]` (safe only under loopback);
  auth deferred (local-first).
- Tests: `tests/compat/test_api_loopback_guarantee.py` (6 tests).

**Rule**: Is the loopback guarantee sound + unavoidable? If yes, authorize
ADR-0007's flip to Accepted (S004-008b will then flip Status + the governance
test, using "loopback-guaranteed" NOT "production-hardened" per S003-014 cond 3).

### 2. ADR-0004 — verify the just-completed promotion
S004-008 already flipped ADR-0004 to Accepted (gate item 1 — TDX implemented
without `NotImplementedError` — is met; S003-014 does not require a fresh review
for ADR-0004, but this review should still confirm soundness). Confirm the
`TDXDataSource` implementation (`src/doge/infrastructure/data_source/tdx.py`,
`tests/test_tdx_adapter.py`) honors the port contract.

### 3. TDX `connect(self, market="cn")` adapter signature
`TDXDataSource.connect` widens the port signature `connect(self) -> None`
(Liskov-compatible — `market` defaults, callable per the port contract; all
conformance tests pass). TDX is stateful + market-specific (unlike stateless
yfinance), so it binds the server family at connect. **Rule**: is this an
acceptable adapter extension, or does it warrant lazy per-market connect in
`download_kline` + a port-signature revisit? (Flagged in commit `b989ef9`.)

### 4. Layer-gate cleanup (§6 green)
Confirm: `grep -rnE "import sqlite3|import duckdb|sqlite3.connect|duckdb.connect"
src/api src/doge/interfaces src/interface` → ZERO hits. The cleanup:
`INoteRepository` port + `SQLiteNoteRepository` (S004-001), `notes.py` +
`query_stock.py` ported off direct DB (S004-002/003). See TR-045/046.

## What to produce
- Verdict: PASS / CONCERNS / FAIL (focused on these 4 questions).
- Explicit authorization (or not) for the ADR-0007 loopback-promotion flip.
- Ruling on the `connect(self, market)` signature (accept / require refactor).
- Output: `production/architecture-reviews/architecture-review-s004-<date>.md`.

## Key files
- ADRs: `docs/architecture/adr-0004-*.md` (Accepted), `adr-0007-*.md` (Proposed).
- Loopback: `src/doge/interfaces/api/main.py` (`_resolve_bind_host`), `tests/compat/test_api_loopback_guarantee.py`.
- TDX: `src/doge/infrastructure/data_source/tdx.py`, `tests/test_tdx_adapter.py`, `src/doge/core/ports/data_source.py`.
- Notes port: `src/doge/core/ports/repository.py` (`INoteRepository`),
  `src/doge/infrastructure/database/repositories.py` (`SQLiteNoteRepository`),
  `tests/unit/doge/test_note_repository.py`.
- Prior review: `production/architecture-reviews/architecture-review-s003-014-2026-06-13.md`.
- Polish pass: `production/qa/evidence/polish-pass-2026-06-14.md`.
- Governance test: `tests/unit/governance/test_adr_lifecycle_status.py`.

## Verification baseline (this session)
- `python -m pytest -q` → 568 passed, 2 skipped, 0 failed.
- §6 grep gate → 0 hits.
- ADR-0004 Accepted; ADR-0007 Proposed (pending this review's sign-off).

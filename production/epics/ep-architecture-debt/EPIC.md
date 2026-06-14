# Epic: Architecture & Clean-Layer Debt

> **Epic Slug**: `ep-architecture-debt`
> **Status**: Proposed
> **Created**: 2026-06-12
> **Sprint**: Sprint 002
> **Control Manifest**: 2026-06-12
> **Governing ADRs**: ADR-0001 (Brownfield Clean Architecture Migration), ADR-0005 (LLM Client Strategy)
> **Source Findings**: `architecture-traceability.md` FINDING-3, FINDING-4; CDD open questions OQ-2, OQ-5, OQ-11

## Overview

This epic retires the **live BUG-class RSRS drift** between the three
implementations (Python scalar, Python vectorized, DuckDB SQL), closes the two
**unresolved clean-architecture port-naming decisions** (cache-port split and
view-service port injection), eliminates the three concrete **forbidden-pattern
offenders** flagged for this sprint, and stops the storage layer from
**silently swallowing write exceptions**. It is the largest epic in Sprint 002
by story count and the one most directly backed by TR-IDs.

## Motivation

The architecture review (`architecture-traceability.md` §6) graded the system
*internally coherent and largely self-consistent*, but surfaced five findings.
Four of them — FINDING-3 (RSRS drift), FINDING-4 (port-naming drift), plus the
forbidden-pattern and swallowed-exception items the CDDs self-flag — land here.
They are not design gaps; they are **implementation drift the CDDs already
document as open**. Leaving them in place means:

- Macro prompt dashboards can embed `nan` RSRS where the momentum scanner emits
  `0.0` (FINDING-3 / TR-016 / OQ-11).
- Story authors and registry writers cannot tell which cache port name is
  canonical (FINDING-4 / OQ-2 / TR-042).
- Four read-only view services take a concrete `DuckDBConnection` adapter with
  no port abstraction (OQ-5 / TR-041) — an ADR-0001-permitted interim step that
  must be formally reconciled.
- Three legacy modules still contain forbidden patterns (TR-011, TR-040) that
  block the Batch-1/2/3 migration gates in `control-manifest.md §7`.
- `save_stock_data_custom` swallows write failures with bare `except: pass`,
  violating the `market-data-storage` acceptance criteria (TR-006).

## Scope

### In Scope

- Unify the RSRS sign convention across all three implementations and add the
  missing guards to the macro local copy.
- Decide the cache-port vs metadata-port split (ADR or registry amendment).
- Decide the view-service port-injection stance (convert to port OR amend ADR-0001).
- Remediate the three named forbidden-pattern offenders.
- Replace the swallowed write exception with a typed, logged
  `StorageWriteError`.

### Out of Scope

- Authoring the missing Module #6 CDD (that is FINDING-2, not in this epic —
  Sprint 002 assumes it stays a known gap; a future sprint owns it).
- Populating `docs/registry/entities.yaml` (FINDING-5 — separate registry-design
  decision, not bundled here).
- TDX adapter migration beyond removing the `sys.path.insert` shim (the full
  TR-011 NotImplementedError removal is its own migration story; this epic only
  clears the shim that blocks Batch-1).
- Raising `retention_days` itself (that lives in `ep-storage-consistency` —
  S002-007 — because it is entangled with the view-window decision).

## Stories

| Story ID | Title | TR-ID | Priority |
|----------|-------|-------|----------|
| S002-001 | RSRS sign-convention unification across Python-scalar / vectorized / DuckDB-SQL | TR-016 (OQ-11) | MED |
| S002-002 | Macro local RSRS copy: add flat-variance + NaN guards | TR-016 | MED |
| S002-003 | Decide cache-port vs metadata-port split (TickerMetadataSource vs Cache/ITickerNameCache) | TR-042 (OQ-2) | MED |
| S002-004 | Decide view-service port injection (IMarketViewRepository OR amend ADR-0001) | TR-041 (OQ-5) | MED |
| S002-005 | Forbidden-pattern remediations (scan.py init_db_custom, MomentumRanker.get_connection sqlite3.connect, tdx_downloader.py sys.path.insert) | TR-011, TR-040 | MED |
| S002-006 | Replace swallowed write exception with logged StorageWriteError | TR-006 | MED |

## Dependencies

- **S002-001 → S002-002**: the macro local-copy guard fix should land after (or
  alongside) the sign-convention unification so the canonical copy is the
  single source of truth first; alternatively S002-002 makes
  `data_loader.calculate_rsrs` delegate to `momentum_scanner.calculate_rsrs`,
  which subsumes S002-001 for the macro path.
- **S002-003 / S002-004** are **design + ADR** stories, not code stories —
  their output is a `/architecture-decision` Proposed ADR (or an ADR-0001
  amendment), which then gates the code-touch stories in a later sprint.
- **S002-005** has no internal dependency but unblocks Batch-1 of the
  `control-manifest.md §7` migration sequence.
- **S002-006** is a prerequisite for the ADR-0003 promotion story (S002-013 in
  `ep-governance-security`) — ADR-0003 cannot move to Accepted while
  `StorageWriteError` is not yet surfaced.

## Acceptance

- [ ] RSRS produces identical sign-convention output across all three
  implementations on identical input (pinned by a cross-implementation parity
  test).
- [ ] Macro local RSRS copy returns `0.0` (not `nan`) on flat/zero-variance and
  short series — pinned by `tests/test_macro_strategist.py`.
- [ ] The cache-port question has a recorded decision (Accepted ADR or ADR-0001
  amendment) — `tr-registry.yaml` TR-042 references the deciding artifact.
- [ ] The view-service port-injection question has a recorded decision
  (Accepted ADR or ADR-0001 amendment) — TR-041 references the deciding artifact.
- [ ] `grep -rnE "import sqlite3|sqlite3\.connect|sys\.path\.insert" src/api src/micro/tdx_downloader.py`
  returns no new offenders for the three named sites (legacy-tolerated
  offenders outside the named three may remain).
- [ ] `save_stock_data_custom` raises / logs `StorageWriteError` on write
  failure instead of bare `except: pass` — pinned by `tests/test_database.py`.

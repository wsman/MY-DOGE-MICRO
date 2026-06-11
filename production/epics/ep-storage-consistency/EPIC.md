# Epic: Storage & Configuration Consistency

> **Epic Slug**: `ep-storage-consistency`
> **Status**: Proposed
> **Created**: 2026-06-12
> **Sprint**: Sprint 002
> **Control Manifest**: 2026-06-12
> **Governing ADRs**: ADR-0002 (Centralized Runtime Configuration), ADR-0003 (Storage Repository Contract)
> **Source Findings**: `architecture-traceability.md` §7 #2 (retention decision), TR-006 (retention), TR-019 (config drift)

## Overview

This epic closes the two **silent-correctness** gaps in the storage and
configuration layers: (1) the **HIGH-severity retention-vs-view-window
mismatch** where `retention_days=180` silently truncates data the
`vw_market_breadth_cn` view tries to read over a 730-day window, and (2) the
**two-sources-of-truth config drift** between `models_config.json`
`scanner_filters` and `Settings().market.*`. Both are bugs the operator will
not see until a breadth scan returns silently-wrong numbers.

## Motivation

These are the two items the architecture review flagged as needing an
**explicit decision, not just an open question** (`architecture-traceability.md`
§7 #2). They are the highest-leverage correctness fixes in Sprint 002:

- **Retention truncation (TR-006, HIGH)** — `market-data-storage.md §9 #1`
  documents that the 180-day retention is already shorter than the 730-day
  `vw_market_breadth_cn` window. The breadth view silently reads fewer rows
  than its window promises. This is a **latent silent-truncation bug** — no
  error, no warning, just wrong breadth numbers once data ages past 180 days.
  Per `control-manifest.md §3`, a Migration/Data-Pipeline story type carries a
  **BLOCKING** apply/rollback-or-dry-run evidence gate.
- **Config drift (TR-019)** — the scanner-filter universe (CN code whitelist
  `^00|30|60|68`, US leveraged-ETF blacklist, liquidity floors `cn 2e8 / us 2e7`,
  US 60-day surge breaker `max_change_pct`) is described in two places that can
  disagree: `models_config.json` `scanner_filters` and
  `Settings().market.*` (ADR-0002 centralized config). ADR-0002's whole purpose
  is one source of truth; the drift undermines it.

## Scope

### In Scope

- Make the retention-vs-view-window relationship **explicit and non-destructive**:
  either raise `DOGE_RETENTION_DAYS` to `>= 730` (the longest view window) with
  a documented safe default, **or** shorten the breadth view window to match
  retention — captured as a decision.
- Add the `DOGE_RETENTION_DAYS` env knob to `Settings()` (ADR-0002) so the
  retention is configurable without source edits.
- Reconcile the two scanner-filter sources: declare one canonical home
  (`Settings().market.*` per ADR-0002) and either remove
  `models_config.json:scanner_filters` or document it as a read-only mirror
  loaded into `Settings()` at startup.

### Out of Scope

- Designing `docs/registry/entities.yaml` (FINDING-5 — separate registry-design
  decision). The retention default and the scanner-filter constants will be
  *proposed* as `entities.yaml` entries once that registry exists, but authoring
  the registry is not this epic's work.
- The `save_stock_data_custom` swallowed-exception fix (that is S002-006 in
  `ep-architecture-debt`) — it shares TR-006 because TR-006 covers both the
  error-surfacing *and* the retention-safe-default requirement, but the two
  stories are split for clean ownership.
- Bootstrapping the `stock_notes` table from `initialize_system_dbs()` (a
  separate cold-start migration gap noted in `architecture-traceability.md`
  "Additional observations").

## Stories

| Story ID | Title | TR-ID | Priority |
|----------|-------|-------|----------|
| S002-007 | Resolve retention_days vs analytical-view window mismatch (raise retention to >=730d OR shorten view) — silent-truncation fix | TR-006 | **HIGH** |
| S002-008 | Reconcile models_config.json scanner_filters vs Settings().market.* — single source of truth | TR-019 | MED |

## Dependencies

- **S002-007 → S002-006** (in `ep-architecture-debt`): both touch TR-006.
  S002-006 surfaces the write error; S002-007 makes the retention default safe.
  They can proceed in parallel but the ADR-0003 promotion story (S002-013 in
  `ep-governance-security`) is gated on **both** being done, because TR-006
  bundles "logged `StorageWriteError`" + "retention safe default >= 730d".
- **S002-008** has no internal dependency; it is a config-layer story governed
  by ADR-0002. It should land before ADR-0002 is promoted to Accepted
  (S002-013) so the promotion reflects the reconciled single-source-of-truth.

## Acceptance

- [ ] `DOGE_RETENTION_DAYS` exists as a `Settings()` knob with a documented
  default `>= 730` (or the breadth view window is documented and tested at
  `<= retention_days`).
- [ ] A breadth scan over data older than the previous 180-day boundary returns
  the window-promised row count, not a silently-truncated set — pinned by a
  migration/dry-run test in `tests/migration/` or `tests/test_database.py`
  (**BLOCKING** gate per `control-manifest.md §3`).
- [ ] Exactly one source defines the scanner-filter universe; the other is
  either removed or documented as a load-time mirror with a test that the two
  cannot diverge.
- [ ] ADR-0002's "one source of truth" intent is verifiable — `Settings()`
  reads the canonical filter values, and `models_config.json` does not
  independently override them at call sites.

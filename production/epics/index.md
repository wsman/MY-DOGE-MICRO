# Epics Index: MY-DOGE-MICRO

> **Status**: Draft
> **Created**: 2026-06-12
> **Sprint**: Sprint 002 — CDD Follow-up & Technical Debt
> **Control Manifest**: 2026-06-12

## Overview

This index tracks the epic groupings for Sprint 002. Sprint 002 captures the
**remaining technical debt** surfaced by the comprehensive architecture review
(`docs/architecture/architecture-traceability.md`) plus the open questions
recorded in the twelve module CDDs. The original Sprint 001 bug backlog
(Bug A `delete_note` soft-delete, Bug B yfinance adapter, Bug C module-#6 rename,
Bug E test coverage) is **RESOLVED**; these epics do **not** re-cover that work.

Each story in each epic embeds a **TR-ID** from
`docs/architecture/tr-registry.yaml` where one exists, so `/create-stories`,
`/story-readiness`, and `/story-done` can trace the requirement end-to-end.

## Epic Index

| Epic Slug | Title | Theme | Stories | Status |
|-----------|-------|-------|---------|--------|
| `ep-architecture-debt` | Architecture & Clean-Layer Debt | RSRS drift, port splits, forbidden-pattern fixes, storage error surfacing | 6 | Proposed |
| `ep-storage-consistency` | Storage & Configuration Consistency | retention vs view-window silent truncation, config single-source-of-truth | 2 | Proposed |
| `ep-api-resilience` | API & Transport Resilience | error envelope, SSE reconnect reliability | 2 | Proposed |
| `ep-governance-security` | Governance, Portability & Security | ADR promotion, @pretext portability, API-key env migration | 3 | Proposed |
| **Total** | | | **13** | |

## Epic Themes

- **Architecture & Clean-Layer Debt** — the RSRS sign-convention divergence
  across three implementations, the macro local-copy guard gap, the two
  unresolved port-naming decisions (cache-port split, view-service port
  injection), the three concrete forbidden-pattern offenders, and the swallowed
  write exception in the storage layer.
- **Storage & Configuration Consistency** — the `retention_days=180` vs the
  730-day `vw_market_breadth_cn` window (a latent **silent-truncation** bug),
  and the two-sources-of-truth drift between `models_config.json` scanner
  filters and `Settings().market.*`.
- **API & Transport Resilience** — the `HTTPException(500, str(e))` internal-
  error leak in the API routers, and the dropped-SSE-stream-without-terminal-
  `progress`-event gap that leaves scan status stuck.
- **Governance, Portability & Security** — promote the two overstretched
  Proposed ADRs whose decisions are already shipped (ADR-0002, ADR-0005), gate
  ADR-0003/0004/0007 promotion on their remediation stories, make the
  `@pretext` sibling-project alias portable, and rotate the locally-shipped
  DeepSeek API key to an env var.

## Story-ID Scheme

All Sprint 002 stories use the prefix **`S002-NNN`** (zero-padded, contiguous
within the sprint, not within an epic). The story-to-epic and story-to-TR-ID
mapping lives in `production/sprints/sprint-002-cdd-followup.md` and the
machine-readable `production/sprint-status.yaml`.

## Related Artifacts

- Sprint plan: `production/sprints/sprint-002-cdd-followup.md`
- Machine-readable status: `production/sprint-status.yaml`
- Findings source: `docs/architecture/architecture-traceability.md` (§6 FINDINGS)
- Requirement IDs: `docs/architecture/tr-registry.yaml`
- Control plane: `docs/architecture/control-manifest.md` (Manifest Version 2026-06-12)
- Module structure: `design/cdd/module-index.md`

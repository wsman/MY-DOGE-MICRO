# ADR-0039: Analyst Product Home

## Status

Accepted

## Date

2026-07-06

## Decision Makers

wsman (product owner) · Codex implementation agent

## Summary

Sprint 030 implements the Analyst Product Home portion of
`C:\Users\WSMAN\.claude\plans\a038a698-harmonic-mango.md`.

The decision is to expand the existing `/home` `HomeDashboardView` from an
operator work queue into an analyst-first, mode-aware product home while keeping
the existing platform shell route, route name, and navigation registry intact.
The Home page now gives analysts direct entry to the Research workspace, recent
runs, recent uploads, recent cases, pending approvals, recent memos, static
portfolio/demo-pack CTAs, and Local Alpha readiness. Developer mode preserves
the existing operator diagnostics.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | TypeScript ~6.0.2; Vue 3.5.32; Pinia 3.0.4; Naive UI 2.44.1 |
| **Domain** | Web platform shell / Research workspace handoff / Governance |
| **Knowledge Risk** | LOW - uses existing stores, routes, and `/v1` adapters only |
| **References Consulted** | `web/src/views/HomeDashboardView.vue`, `web/src/stores/platform.ts`, `web/src/stores/documents.ts`, `web/src/api/agent.ts`, `docs/architecture/adr-0032-workspace-mode-and-memo-export.md`, `docs/architecture/adr-0036-run-list-and-comparison.md`, `C:\Users\WSMAN\.claude\plans\a038a698-harmonic-mango.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | Focused Home Web tests, full Web test/build, docs/maturity validators, SDK contract, plan closure gate |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0020 (Platform Shell UI), ADR-0028 (Additive Session Turn Workflow Field), ADR-0032 (Workspace Mode And Memo Export), ADR-0036 (Run List And Comparison), ADR-0038 (Cross-Surface Handoff Closure) |
| **Enables** | A five-minute Local Alpha entry path from Home to research run, citation review, approval, export, and readiness review |
| **Blocks** | None |
| **Ordering Note** | This ADR is Web product-surface closure. New list APIs, SDK helpers, memo editing, and production gate closure require separate designs. |

## Context

### Problem Statement

The platform shell already routes `/` to `/home`, but Home only showed an
operations work queue: pending cases, failed/degraded runs, recent executions,
and data freshness warnings. Analysts landing on Home still had to know where
to start research, where recent runs and uploads were visible, and how the
current Local Alpha readiness posture related to their work.

### Constraints

- Preserve the current maturity posture: `production_ready: false`,
  `stable_declaration: forbidden`, and Level 3 `experimental`.
- Do not add, remove, or rename `/v1` routes or HTTP response fields.
- Do not change SDK package source or the 15-surface SDK contract.
- Do not change the route name `home-dashboard`, `PRIMARY_SCENARIO_NAV_ITEMS`,
  `splitTree`, registry IDs, or `App.vue`.
- Do not introduce a portfolio list or demo-pack list API.
- Do not close external/operator gates.

### Requirements

- Add a Home start band with `Start research` and a zero-key `Run demo` action.
- Render recent runs using the existing `RunComparisonPanel`.
- Add a recent uploads card using the existing document list path.
- Surface recent cases, pending approvals, recent memos, pending cases, and
  recent executions from existing platform store data.
- Add static CTAs for portfolio import and demo-pack generation without live
  list calls.
- Render Local Alpha readiness via the existing `MaturityPanel`.
- Keep failed/degraded runs and data freshness warnings hidden in Analyst mode
  and visible in Developer mode.
- Add focused Home tests and governance evidence.

## Decision

Expand `HomeDashboardView.vue` in place.

Home now loads only existing data sources:

```text
loadHomeQueue(20)
loadResearchCases({ limit: 10 })
documentStore.loadDocuments()
RunComparisonPanel -> listAgentRuns(8)
MaturityPanel -> /v1/capabilities
```

The `Run demo` button sets a known sample workflow (`earnings_review`), clears
document and portfolio selection, calls the existing agent store run path, and
routes to `/research-agent` only after the run state exists. This prevents Home
from depending on hidden document upload state.

Portfolio and demo-pack entries are static CTAs because the current product has
`POST /v1/portfolios/import` and CLI `doge demo-pack`, but no list endpoints for
either concept. Adding those endpoints is outside this sprint.

### Key Interfaces

```text
/home
/research-agent
/runs/{run_id}
/cases/{case_id}
HomeDashboardView.vue
HomeRecentUploads.vue
HomeStaticCtas.vue
```

## Alternatives Considered

### Alternative 1: Add a separate landing page

- **Description**: Create a new route for product Home and leave `/home` as the
  operator queue.
- **Pros**: Clean separation of analyst and operator surfaces.
- **Cons**: Adds routing and registry churn, and risks fragmenting first-run
  entry points.
- **Rejection Reason**: The plan explicitly expands the existing Home surface.

### Alternative 2: Add `GET /v1/portfolios` and demo-pack list APIs

- **Description**: Back every Home card with live lists.
- **Pros**: More complete dashboard data.
- **Cons**: Expands the API and SDK contract beyond the Web-only Home sprint.
- **Rejection Reason**: Static CTAs satisfy the current workflow without a new
  wire contract.

### Alternative 3: Move operator diagnostics to a new admin page

- **Description**: Remove failed-run and data-freshness panels from Home.
- **Pros**: Cleaner analyst view.
- **Cons**: Loses an existing local operator path and adds navigation work.
- **Rejection Reason**: Developer mode can preserve diagnostics without route
  churn.

## Consequences

### Positive

- Analysts can start from Home and reach the Research workspace directly.
- Recent runs, uploads, cases, approvals, memos, readiness, and static handoff
  actions are visible in one place.
- Developer mode retains the existing operator diagnostics.
- The change uses existing stores and panels, so the `/v1` and SDK contracts do
  not grow.

### Negative

- Portfolio and demo-pack cards are static CTAs, not live inventory cards.
- Home now mounts several existing readers at once; tests must mock the
  self-loading panels.
- The Analyst/Developer mode is shared with the Research workspace because it
  uses the global agent store persona toggle.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Home over-fetches on mount | MEDIUM | LOW | Use bounded existing calls and self-loading panels with small limits. |
| Demo run uses stale global agent state | MEDIUM | MEDIUM | Home clears document and portfolio IDs and sets a known sample workflow before running. |
| Analysts miss operator diagnostics | LOW | LOW | Developer mode exposes the existing failed/degraded and freshness panels. |
| Static CTAs appear less complete than live cards | MEDIUM | LOW | ADR records that live list APIs are deliberately out of scope. |

## CDD Requirements Addressed

| CDD Document | Requirement | How This ADR Addresses It |
|--------------|-------------|----------------------------|
| `design/cdd/sprint-030-analyst-product-home.md` | Home should provide an analyst-first start surface without new backend contracts. | Expands `/home` using existing stores, routes, and panels. |
| `design/cdd/sprint-ux-5-workspace-modes-and-export.md` | Analyst and Developer modes should separate business review from diagnostics. | Reuses the global persona toggle and gates operator diagnostics in Developer mode. |
| `design/cdd/sprint-026-demo-pack-and-sdk-cookbooks.md` | Demo pack handoff should remain a local CLI workflow. | Adds a static Home CTA rather than a daemon list API. |
| `design/cdd/sprint-027-run-comparison.md` | Recent run comparison should be visible to users. | Embeds `RunComparisonPanel` in Home. |

## Performance Implications

- **CPU**: Small client-side rendering cost for bounded lists.
- **Memory**: Home holds existing store snapshots already used elsewhere.
- **Network**: No new endpoint; Home issues existing bounded reads.
- **Web Load Time**: Home chunk grows by the new local cards and existing panel
  imports; Web build remains passing.

## Migration Plan

1. Expand `HomeDashboardView.vue` in place.
2. Add `HomeRecentUploads.vue` and `HomeStaticCtas.vue`.
3. Add focused Home and component tests.
4. Update governance docs and Home reader docs.
5. Run focused Web tests, full Web test/build, SDK contract, docs validators,
   plan closure, and whitespace checks.

## Validation Criteria

- Home shows start research, run demo, recent runs, recent uploads, pending
  approvals, recent cases, recent memos, static CTAs, pending cases, recent
  executions, and readiness.
- Operator diagnostics are hidden in Analyst mode and visible in Developer mode.
- `Start research` routes to `/research-agent`.
- `Run demo` uses `earnings_review`, clears document/portfolio IDs, and routes
  after creating a run.
- Product navigation route/registry tests remain unchanged.
- Web tests and build pass.
- SDK contract remains 15/15.
- Docs authority, links, maturity claims, alpha honesty, plan closure, and
  whitespace checks pass.

## Related Decisions

- ADR-0020: Platform Shell UI
- ADR-0028: Additive Session Turn Workflow Field
- ADR-0032: Workspace Mode And Memo Export
- ADR-0036: Run List And Comparison
- ADR-0038: Cross-Surface Handoff Closure

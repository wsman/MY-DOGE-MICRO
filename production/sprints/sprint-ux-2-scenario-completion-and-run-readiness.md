# Sprint UX-2 — Scenario Completion & Run-Readiness

> Status: **Local Implementation Complete / Ready for Local Acceptance**
> Branch: `main` · Date: 2026-07-05 · Baseline HEAD: `6aff3ca`
> Plan: `C:\Users\WSMAN\.claude\plans\agent-quizzical-wolf.md`
> CDD: [design/cdd/sprint-ux-2-scenario-completion-and-run-readiness.md](../../design/cdd/sprint-ux-2-scenario-completion-and-run-readiness.md)
> Manifest: [sprint-ux-2-review-reconciliation-manifest.md](../qa/evidence/sprint-ux-2-review-reconciliation-manifest.md)
> Predecessor: [Sprint UX-1](sprint-ux-1-first-run-coherence.md)

## Context

UX-2 closes the genuine local remainder from the repeated strategic review
after UX-1. The P0 first-run commands were already shipped in UX-1; this sprint
instead makes the first result path more complete: README starts with
`doge start`, Web scenario selection can browse workflow templates while
falling back when the feature flag is off, the workspace shows run preflight
checks before execution, built-in workflow templates include Risk Alert and
Portfolio Impact Note, and `doge brief` produces a console market brief from
local CN views.

The sprint changes product UX and local CLI behavior only. It does not change
the `/v1` wire contract, SDK public surface, runtime maturity, or external gate
state.

## Delivered Slices

### Slice 0 — Reconciliation Manifest

`production/qa/evidence/sprint-ux-2-review-reconciliation-manifest.md` records
34 review claims, their evidence-backed verdicts, and the exact slice mapping.
It keeps stale UX-1 work, deferred product polish, external/operator gates, and
the ADR-0021 taxonomy conflict out of this sprint's implementation scope.

### Slice 1 — README First-Run Pointer

`README.md` Quick Start now installs the package and immediately points new
operators to `doge start`, then explains that the launcher routes to CLI,
daemon, Web, demo, or readiness checks. Existing Local Alpha maturity wording is
unchanged.

### Slice 2 — ScenarioPicker Live-Browse

`web/src/components/agent/ScenarioPicker.vue` now reads
`platformStore.workflowTemplates` and triggers `loadWorkflowTemplates()` on
mount. Because `/v1/workflow-templates` is feature-flagged and defaults off,
the four UX-1 scenarios remain the first-paint fallback and the error/empty
state fallback.

### Slice 3 — Workflow Template Completion

`src/doge/platform/workspace/template_seed.py` adds:

- `risk_alert`
- `portfolio_impact_note`

Both follow the existing built-in template contract shape and are covered by
`tests/unit/workspace_workflow/test_template_seed.py`.

### Slice 4 — Run Preflight Checklist

`web/src/components/agent/RunPreflightChecklist.vue` is rendered before the Run
button in `ResearchAgentView`. It checks selected market, selected documents,
portfolio import, and Kimi provider configuration from existing stores. Missing
documents, portfolio, or provider configuration warn but do not block the run.

### Slice 5 — `doge brief`

`doge brief` is an additive console market brief command. It reuses
`GenerateMarketOverviewUseCase.brief()` to render six sections to stdout:
Market Regime, Breadth, Momentum Leaders, Volume Anomalies, Watchlist, and
Suggested Research Questions. The existing file-writing market overview path
is unchanged. The command defaults to CN local data and explicitly returns
non-zero for `--market us` because the current brief depends on CN local views.

### Slice 6 — Governance Closeout

This sprint record, the UX-2 CDD, the reconciliation manifest, and the active
session-state rotation record UX-2 as a local acceptance sprint. UX-2 is not
registered in `production/sprint-status.yaml`, following the UX-1
product-acceptance precedent.

## Posture

- `production_ready: false`; `stable_declaration: forbidden`; `level_3_sdk_platform: experimental`.
- External/operator gates S017-003 / W3-live / AUTH-prod / S017-007 remain open.
- S017-002 and S017-006 remain passed.
- No external evidence was fabricated.
- No `/v1` wire-contract or SDK public-surface change.

## Verification

Focused verification completed during implementation:

- Python: `py -3 -m pytest tests\cli\test_cli_brief.py tests\unit\workspace_workflow\test_template_seed.py tests\test_market_reporting.py tests\cli\test_cli_arg_parsing.py -q` => **34 passed**.
- Web: `cd web && npm run test -- src/components/agent/ScenarioPicker.spec.ts src/components/agent/RunPreflightChecklist.spec.ts src/views/ResearchAgentView.spec.ts` => **9 passed**.
- Web build: `cd web && npm run build` => **passed**.
- Docs/governance: docs authority, docs maturity claims, alpha maturity honesty,
  docs links (86 markdown files), import boundaries, SDK contract, and plan
  closure with `--source-plan` all passed.
- CLI smoke: template seed dry-run listed all 10 built-ins; `doge brief --market cn`
  printed all six sections with local no-data placeholders; `doge brief --market us`
  exited non-zero with a clear unavailable-data message.

## Non-Goals

- No Analyst/Developer mode split.
- No conclusion-evidence matrix.
- No approval schema expansion.
- No artifact export or run comparison.
- No SDK cookbook directory.
- No `doge demo-pack`.
- No daemon operator status expansion.
- No per-status `next_actions` contract.
- No external/operator gate closure.

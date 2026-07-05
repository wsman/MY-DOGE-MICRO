# Sprint UX-2 — Scenario Completion & Run-Readiness Reconciliation Manifest

> Sprint: UX-2 (Scenario Completion & Run-Readiness)
> Date: 2026-07-05 · Baseline HEAD: `6aff3ca` · Branch: `main`
> Plan: `C:\Users\WSMAN\.claude\plans\agent-quizzical-wolf.md`
> Status: Local implementation complete; final gate evidence is recorded in the sprint record.
> Predecessor: [Sprint UX-1](../../sprints/sprint-ux-1-first-run-coherence.md)

## Purpose

This manifest is the D0 decision gate for UX-2. It reconciles the repeated
strategic review against the current repository, rejects already-shipped or
operator-owned scope, and limits implementation to the genuine local remainder:
README first-run discovery, live-browsed scenario templates with fallback, two
additional built-in workflow templates, a Web run-readiness checklist, and a
console market brief.

Posture is unchanged: `production_ready: false`,
`stable_declaration: forbidden`, Level 1/2 Alpha, and Level 3
`experimental`. External/operator gates remain open for S017-003, W3-live,
AUTH-prod, and S017-007; S017-002 and S017-006 remain passed.

## Verdict Taxonomy

- **STALE** — the review claim describes a missing item that already shipped.
- **DONE** — the claim is already true in current code/docs and needs no work.
- **NEW_WORK** — local work intentionally closed by UX-2.
- **DEFERRED** — valid local idea, but outside this sprint.
- **EXTERNAL / OPERATOR-GATED** — requires operator/live evidence; UX-2 cannot close it.
- **ADR-CONFLICT** — conflicts with accepted architecture decisions and is rejected.

## Claim Table

| ID | Claim / recommendation | Verdict | Evidence | UX-2 action |
|---|---|---|---|---|
| A1 | `doge start` missing from parser/dispatch | STALE | `src/doge/interfaces/cli/main.py:115-123`, `src/doge/interfaces/cli/main.py:231-247`, `tests/cli/test_cli_start.py` | none |
| A2 | `doge doctor --next` missing from parser | STALE | `src/doge/interfaces/cli/main.py:106-113`, `src/doge/interfaces/cli/commands/doctor.py` | none |
| A3 | README lacks top-level `doge start` path | NEW_WORK | `README.md:19-31` after Slice 1 | Slice 1 |
| A4 | CLI REPL needs `/status` and grouped `/help` | STALE | UX-1 record `production/sprints/sprint-ux-1-first-run-coherence.md` | none |
| A5 | Shared run-status labels needed | STALE | `src/doge/interfaces/cli/run_status_labels.py`, `web/src/utils/runStatus.ts` | none |
| B1 | Web needs run preflight checklist | NEW_WORK | `web/src/components/agent/RunPreflightChecklist.vue`, `web/src/views/ResearchAgentView.vue` | Slice 4 |
| B2 | Analyst Mode / Developer Mode | DEFERRED | Needs broader workspace layout change | future sprint |
| B3 | Conclusion-evidence matrix | DEFERRED | Blocked on structured memo/claim matrix shape | future sprint |
| B4 | Approval explanation fields | DEFERRED | Requires SDK/domain schema coordination | future sprint |
| B5 | Artifact export controls | DEFERRED | Product polish beyond run-readiness | future sprint |
| B6 | Run comparison | DEFERRED | Needs run-retention/list endpoint design | future epic |
| B7 | ScenarioPicker should browse templates | NEW_WORK | `web/src/components/agent/ScenarioPicker.vue`, `ScenarioPicker.spec.ts` | Slice 2 |
| B8 | Empty-state CTAs missing | STALE | `web/src/components/agent/EmptyStateCtas.vue` | none |
| B9 | MaturityPanel / ScenarioPicker / GuidedFlow missing | STALE | UX-1 record and Web components | none |
| C1 | Python SDK cookbook files | DEFERRED | SDK README already has inline quickstart; cookbook is separate packaging scope | future sprint |
| C2 | TypeScript SDK cookbook files | DEFERRED | SDK README already has inline quickstart; cookbook is separate packaging scope | future sprint |
| C3 | SDK README quickstart missing | DONE | `packages/doge-sdk-python/README.md`, `packages/doge-sdk-typescript/README.md` | none |
| D1 | `doge demo-pack` command | DEFERRED | Screenshot/export packet is its own demo sprint | future sprint |
| D2 | Demo packet artifacts | DEFERRED | Depends on D1 and screenshot capture policy | future sprint |
| E1 | `doge market brief` / market daily brief | NEW_WORK | Implemented as `doge brief`; `src/doge/interfaces/cli/commands/brief.py` | Slice 5 |
| E2 | Missing `risk_alert` / `portfolio_impact_note` templates | NEW_WORK | `src/doge/platform/workspace/template_seed.py` | Slice 3 |
| E3 | Portfolio import auto-summary | DEFERRED | Web portfolio UX polish beyond run-readiness | future sprint |
| E4 | Governance workflow progress view | DEFERRED | Needs gateway contract/persistence shape | future epic |
| F1 | Three runtime levels unclear | DONE | `docs/architecture/runtime-levels.md`, `README.md` | none |
| F2 | Value scenarios vs user paths unclear | DONE | `docs/product/user-scenarios.md`, Sprint 021 record | none |
| F3 | Five platform capability modules should be canonical | ADR-CONFLICT | ADR-0021 uses 4 product + 4 platform bounded contexts | reject |
| F4 | README At A Glance missing | DONE | `README.md` Architecture At A Glance | none |
| F5 | API docs should center five `/v1` families | DONE | `docs/API.md`, Sprint I/018 records | none |
| G1 | Financial provider fixture approval | EXTERNAL / OPERATOR-GATED | closure gate S017-003 open | none |
| G2 | Analyst/citation-quality benchmark | EXTERNAL / OPERATOR-GATED | closure gate W3-live open | none |
| G3 | Browser/manual reconnect evidence | EXTERNAL / OPERATOR-GATED | W3-live-dependent manual evidence remains operator-owned | none |
| G4 | AUTH-prod validation | EXTERNAL / OPERATOR-GATED | closure gate AUTH-prod open | none |
| G5 | Production retrieval quality | EXTERNAL / OPERATOR-GATED | provider/operator production retrieval evidence absent | none |
| G6 | SDK registry approval | EXTERNAL / OPERATOR-GATED | closure gate S017-007 open | none |

## Slice Register

| Slice | Scope | Files |
|---|---|---|
| 0 | Manifest gate | `production/qa/evidence/sprint-ux-2-review-reconciliation-manifest.md` |
| 1 | README first-run pointer | `README.md` |
| 2 | ScenarioPicker live-browse with fallback | `web/src/components/agent/ScenarioPicker.vue`, `ScenarioPicker.spec.ts` |
| 3 | Built-in workflow templates | `src/doge/platform/workspace/template_seed.py`, `tests/unit/workspace_workflow/test_template_seed.py` |
| 4 | Run preflight checklist | `web/src/components/agent/RunPreflightChecklist.vue`, `RunPreflightChecklist.spec.ts`, `web/src/views/ResearchAgentView.vue`, `ResearchAgentView.spec.ts` |
| 5 | Console market brief | `src/doge/application/use_cases/generate_market_overview.py`, `src/doge/interfaces/cli/commands/brief.py`, `src/doge/interfaces/cli/commands/__init__.py`, `src/doge/interfaces/cli/main.py`, `docs/CLI.md`, `tests/cli/test_cli_brief.py`, `tests/cli/test_cli_arg_parsing.py`, `tests/test_market_reporting.py` |
| 6 | Governance closeout | `production/sprints/sprint-ux-2-scenario-completion-and-run-readiness.md`, `design/cdd/sprint-ux-2-scenario-completion-and-run-readiness.md`, `production/session-state/active.md` |

## Posture Invariants

- `production_ready: false`; `stable_declaration: forbidden`; `level_3_sdk_platform: experimental`.
- No `/v1` wire-contract change.
- No SDK public-surface change.
- No external/operator gate closure and no fabricated live evidence.
- UX-2 is not registered in `production/sprint-status.yaml`; it is a UX/product-acceptance sprint, matching the UX-1 precedent.

## Verification Evidence

Focused checks already run during implementation:

```text
py -3 -m pytest tests\cli\test_cli_brief.py tests\unit\workspace_workflow\test_template_seed.py tests\test_market_reporting.py tests\cli\test_cli_arg_parsing.py -q
=> 34 passed

cd web && npm run test -- src/components/agent/ScenarioPicker.spec.ts src/components/agent/RunPreflightChecklist.spec.ts src/views/ResearchAgentView.spec.ts
=> 9 passed

cd web && npm run build
=> passed

py -3 scripts\validate_docs_authority.py
py -3 scripts\validate_docs_maturity_claims.py
py -3 scripts\validate_alpha_maturity_honesty.py
py -3 scripts\validate_docs_links.py
py -3 scripts\validate_import_boundaries.py
py -3 tools\ci\sdk-contract-check.py
py -3 scripts\validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/agent-quizzical-wolf.md
=> passed; plan closure remains 4 open / 2 passed
```

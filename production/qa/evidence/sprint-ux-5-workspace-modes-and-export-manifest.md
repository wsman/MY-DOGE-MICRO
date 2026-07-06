# Sprint UX-5 — Workspace Modes and Export Manifest

> Sprint: UX-5 (B2 Workspace Modes + B5 Artifact Export)
> Date: 2026-07-05
> Status: Local implementation complete; ready for local acceptance.

## Scope

This manifest records local evidence for completing Analyst/Developer workspace
mode and browser-local memo export/copy actions.

## Implementation Evidence

| Area | Evidence |
|---|---|
| ADR | `docs/architecture/adr-0032-workspace-mode-and-memo-export.md` records the Web-local mode/export decision and non-goals. |
| CDD | `design/cdd/sprint-ux-5-workspace-modes-and-export.md` records acceptance criteria. |
| Store state | `web/src/stores/agent.ts` owns `analystMode` and `setAnalystMode` without sending mode state in run payloads. |
| Workspace mode UI | `web/src/views/ResearchAgentView.vue` adds Analyst/Developer controls and hides developer diagnostics with `v-if`. |
| Export utilities | `web/src/utils/memoExport.ts` handles IC question extraction, citation normalization/dedupe, Web-local JSON payloads, downloads, copy fallback, and memo filenames. |
| Export actions | `web/src/views/ResearchAgentView.vue` wires Markdown, JSON, Copy IC Questions, Copy citations, and Print buttons. |
| Utility tests | `web/src/utils/memoExport.spec.ts` pins IC question parsing, citation normalization/dedupe, payload shape, and local filenames. |
| View tests | `web/src/views/ResearchAgentView.spec.ts` pins mode visibility and export/copy/print actions. |
| Store tests | `web/src/__tests__/agentStore.spec.ts` pins Analyst mode default and local-only payload behavior. |

## Verification Commands

```bash
cd web && npm run test -- src/utils/memoExport.spec.ts src/views/ResearchAgentView.spec.ts src/__tests__/agentStore.spec.ts src/components/agent/ConclusionEvidenceMatrix.spec.ts src/components/agent/CitationDrilldown.spec.ts src/utils/runStatus.spec.ts && npm run build
py -3 tools/ci/sdk-contract-check.py
py -3 scripts/validate_docs_authority.py
py -3 scripts/validate_alpha_maturity_honesty.py --file README.md
py -3 scripts/validate_docs_links.py
py -3 scripts/validate_import_boundaries.py
py -3 scripts/validate_docs_maturity_claims.py
py -3 scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0032-workspace-mode-and-memo-export.md
py -3 scripts/validate_alpha_maturity_honesty.py --file design/cdd/sprint-ux-5-workspace-modes-and-export.md
py -3 scripts/validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/agent-quizzical-wolf.md
git diff --check
```

## Verification Results

| Gate | Result |
|---|---|
| UX-5 Web focused suite | Passed: 3 test files, 13 tests. |
| Combined UX-4 + UX-5 Web focused suite | Passed: 6 test files, 25 tests. |
| Web build | Passed: `vue-tsc -b && vite build`. |
| SDK contract | Passed: 13 surfaces, 13 entity parity checks. |
| Docs authority | Passed. |
| README maturity guard | Passed. |
| Docs links | Passed: 90 markdown files validated. |
| Import boundaries | Passed. |
| Docs maturity claims | Passed. |
| ADR/CDD/plan maturity guard | Passed for ADR-0032, UX-5 CDD, and `agent-quizzical-wolf.md`. |
| Plan closure | Passed with controlled-open posture: 4 open / 2 passed. |
| Whitespace | `git diff --check` passed. |

## Posture

- Production posture unchanged.
- No external/operator gates are closed by this sprint.
- No `/v1`, SDK, persistence, runtime event, artifact authority, or citation
  authority change is part of this sprint.
- PDF remains browser print only; no headless-render dependency was added.

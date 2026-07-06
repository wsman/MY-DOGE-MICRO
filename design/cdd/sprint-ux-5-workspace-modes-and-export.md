# Sprint UX-5 CDD: Workspace Modes and Export

Status: Ready for Acceptance
Date: 2026-07-05

## User Promise

An analyst reviewing a Research Agent run can stay in a clean decision-review
workspace by default, while a developer can reveal raw runtime diagnostics when
needed. The analyst can also export or copy memo handoff material without
manual text selection.

## Delivered Contract

Sprint UX-5 completes B2 and B5 from
`C:\Users\WSMAN\.claude\plans\agent-quizzical-wolf.md`:

- Web ResearchAgentView defaults to Analyst mode.
- Developer mode reveals token count, Cost/Eval details, routing tags, raw
  event timeline, and compact JSON payloads.
- Analyst mode keeps memo, input controls, run status, next actions, approvals,
  maturity disclosure, conclusion-evidence matrix, and citation drilldown.
- `web/src/stores/agent.ts` owns UI-only `analystMode` state and does not send
  that state in run-creation payloads.
- `web/src/utils/memoExport.ts` provides local Markdown download, Web-local JSON
  export payload, IC Questions extraction, citation collection/deduplication,
  clipboard copy, and browser print support.
- PDF export remains browser print only; no headless-render dependency was
  added.

## Non-Goals

- No `/v1` export route.
- No SDK method, SDK type, or SDK parity entry.
- No persistence schema or migration.
- No server-side PDF renderer.
- No change to runtime event emission, artifact assembly, or citation authority.
- No external/operator gate closure.
- Current maturity posture remains `production_ready: false`,
  `stable_declaration: forbidden`, and Level 3 `experimental`.

## Acceptance Criteria

- Analyst mode is the default for new agent-store instances.
- Analyst mode hides token count, Cost/Eval, routing tags, raw timeline, and
  compact JSON payloads with `v-if`, not CSS-only hiding.
- Developer mode reveals those diagnostics.
- ResearchAgentView export actions are disabled when no memo exists.
- Markdown export downloads the exact memo content.
- JSON export includes run metadata, memo artifact metadata, memo markdown,
  structured claims, normalized citations, IC questions, and metrics.
- JSON export does not include raw event/timeline payloads.
- Copy IC Questions copies only the memo question section when present.
- Copy citations copies normalized source/page/snippet lines.
- Print uses `window.print()`.
- Focused Web tests and Web build pass.
- Governance validators pass and closure posture remains controlled-open.

## Validation Plan

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

## Local Verification Result

- Initial focused UX-5 Web suite passed: 3 files / 13 tests.
- Combined UX-4 + UX-5 Web focused suite passed: 6 files / 25 tests.
- Web build passed.
- SDK contract check passed at 13 surfaces / 13 parity.
- Docs authority, README maturity, docs links, import boundaries, docs maturity
  claims, ADR/CDD/plan maturity guards, plan closure, and whitespace checks
  passed.
- Closure posture remained `4 open / 2 passed`.

## Out of Scope

- Daemon operator panel.
- Portfolio path-depth improvements.
- SDK cookbook files.
- Demo pack generation.
- Run comparison.
- Governance workflow progress visualization.

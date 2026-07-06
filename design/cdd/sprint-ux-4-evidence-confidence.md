# Sprint UX-4 CDD: Evidence Confidence and Next Actions

Status: Ready for Acceptance
Date: 2026-07-05

## User Promise

An analyst reviewing a completed research run can inspect each conclusion,
understand its support state, and open the exact evidence behind it without
manually matching memo text to the generic source list. When a run is not ready
for review, the status area should also say what the operator can do next.

## Delivered Contract

Sprint UX-4 completes B3 Phase 2 using the Sprint 023 structured-claim contract.
It is a Web + CLI label-only sprint:

- Web renders a `ConclusionEvidenceMatrix` from
  `AgentArtifact.data.structured_claims`.
- Each claim row shows claim text, support status, numeric-check status, risk
  level, and evidence chips.
- Clicking an evidence chip drives `CitationDrilldown` in controlled mode with
  the selected claim's evidence refs.
- `CitationDrilldown` keeps its existing artifact/event/memo scanning fallback.
- Web and CLI expose per-status next-action hints for the existing eight
  `RunStatus` values.

## Non-Goals

- No `/v1` response-model or route change.
- No TypeScript SDK public-surface change.
- No new persistence table or migration.
- No `RunStatus` enum change.
- No matrix sorting, saved filters, run comparison, or governance progress view.
- No external/operator gate closure.
- Current maturity posture remains `production_ready: false`,
  `stable_declaration: forbidden`, and Level 3 `experimental`.

## Acceptance Criteria

- `CitationDrilldown` supports controlled records/modelValue props and still
  supports the existing uncontrolled source-scanning mode.
- `ConclusionEvidenceMatrix` renders structured claims and emits selected
  evidence with its owning claim id.
- ResearchAgentView replaces the compact claim list with the matrix and opens
  the drawer for selected evidence.
- ResearchAgentView status banner shows the first next-action hint for the
  current run status.
- `runStatus.ts` and `run_status_labels.py` define next actions for exactly the
  eight backend `RunStatus` values.
- CLI REPL `/status` prints the current next-action hint.
- Focused Web and Python tests pass.
- SDK contract count remains unchanged at 13 surfaces / 13 parity.
- Closure gate remains `4 open / 2 passed`.

## Validation Plan

```bash
cd web && npm run test -- src/components/agent/ConclusionEvidenceMatrix.spec.ts src/components/agent/CitationDrilldown.spec.ts src/views/ResearchAgentView.spec.ts src/utils/runStatus.spec.ts && npm run build
py -3 -m pytest tests/unit/interfaces/test_run_status_labels.py tests/cli/test_cli_session.py -q
py -3 tools/ci/sdk-contract-check.py
py -3 scripts/validate_docs_authority.py
py -3 scripts/validate_alpha_maturity_honesty.py --file README.md
py -3 scripts/validate_docs_links.py
py -3 scripts/validate_import_boundaries.py
py -3 scripts/validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/agent-quizzical-wolf.md
git diff --check
```

## Local Verification Result

- Focused Web suite passed: 4 files / 15 tests.
- Focused Python CLI suite passed: 23 tests.
- Web build passed.
- SDK contract check passed at 13 surfaces / 13 parity.
- Docs authority, README maturity, docs links, import boundaries, plan closure,
  and whitespace checks passed.
- Closure posture remained `4 open / 2 passed`.

## Out of Scope

- Analyst/Developer mode.
- Artifact export and SDK cookbook files.
- Demo pack generation.
- Portfolio auto-summary.
- Daemon operator panel.
- Run comparison and governance workflow-progress epics.

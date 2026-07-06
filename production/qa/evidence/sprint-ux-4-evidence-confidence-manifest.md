# Sprint UX-4 — Evidence Confidence and Next Actions Manifest

> Sprint: UX-4 (B3 Phase 2 Evidence Confidence)
> Date: 2026-07-05
> Status: Local implementation complete; ready for local acceptance.

## Scope

This manifest records the local evidence for completing the conclusion-evidence
matrix interaction and per-status next-action hints.

## Implementation Evidence

| Area | Evidence |
|---|---|
| ADR | `docs/architecture/adr-0031-conclusion-evidence-matrix-interaction.md` records the interaction decision and non-goals. |
| CDD | `design/cdd/sprint-ux-4-evidence-confidence.md` records acceptance criteria. |
| Citation drawer | `web/src/components/agent/CitationDrilldown.vue` supports controlled records while preserving fallback scanning. |
| Matrix UI | `web/src/components/agent/ConclusionEvidenceMatrix.vue` renders claim rows and evidence chips. |
| Web wiring | `web/src/views/ResearchAgentView.vue` links selected claim evidence to the drawer and status next actions. |
| Web labels | `web/src/utils/runStatus.ts` provides next-action hints for existing run statuses. |
| CLI labels | `src/doge/interfaces/cli/run_status_labels.py` provides matching next-action hints. |
| CLI REPL | `src/doge/interfaces/cli/commands/session_interactive.py` renders the next-action hint in `/status`. |

## Verification Commands

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

## Verification Results

| Gate | Result |
|---|---|
| Web focused suite | Passed: 4 test files, 15 tests. |
| Web build | Passed: `vue-tsc -b && vite build`. |
| Python focused suite | Passed: 23 tests in `tests/unit/interfaces/test_run_status_labels.py` and `tests/cli/test_cli_session.py`. |
| SDK contract | Passed: 13 surfaces, 13 entity parity checks. |
| Docs authority | Passed. |
| README maturity guard | Passed. |
| Docs links | Passed: 89 markdown files validated. |
| Import boundaries | Passed. |
| Plan closure | Passed with controlled-open posture: 4 open / 2 passed. |
| Whitespace | `git diff --check` passed. |

## Posture

- Production posture unchanged.
- Closure gate remains `4 open / 2 passed`.
- No external/operator gates are closed by this sprint.
- No `/v1`, SDK, persistence, or `RunStatus` enum change is part of this sprint.
